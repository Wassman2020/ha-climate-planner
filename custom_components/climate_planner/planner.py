"""Runtime object: storage, season handling and the minute-by-minute engine."""

from __future__ import annotations

import copy
from datetime import date, datetime, timedelta
import logging
from typing import Any
import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import engine
from .const import (
    EVENT_ACTION,
    SIGNAL_UPDATE,
    STORAGE_KEY,
    STORAGE_VERSION,
    default_data,
)

_LOGGER = logging.getLogger(__name__)


class Planner:
    """Holds the configuration and drives the climate entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.data: dict[str, Any] = default_data()
        self.last_actions: dict[str, dict[str, Any]] = {}
        self._unsubs: list[CALLBACK_TYPE] = []

    # ------------------------------------------------------------------ storage
    async def async_load(self) -> None:
        stored = await self.store.async_load() or {}
        data = default_data()
        data.update(stored)
        data.setdefault("presence_rules", [])
        for schedule in data["schedules"]:
            if "seasons" not in schedule:
                schedule["seasons"] = [schedule.pop("season", self.data["season"])]
            schedule.setdefault("enabled", True)
            schedule.setdefault("off_outside", True)
        self.data = data

    @callback
    def _changed(self) -> None:
        self.store.async_delay_save(lambda: self.data, 1)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    async def async_flush(self) -> None:
        await self.store.async_save(self.data)

    def as_dict(self) -> dict[str, Any]:
        out = copy.deepcopy(self.data)
        out.pop("last_boundary", None)
        out["last_actions"] = copy.deepcopy(self.last_actions)
        return out

    # ---------------------------------------------------------------- lifecycle
    @callback
    def start(self) -> None:
        self._unsubs.append(async_track_time_change(self.hass, self._async_tick, second=0))
        self._unsubs.append(async_at_started(self.hass, self._async_on_started))

    @callback
    def stop(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()

    async def _async_on_started(self, _hass: HomeAssistant) -> None:
        changed = await self._async_check_season(dt_util.now().date())
        # A season change already resyncs; otherwise honour resync_on_start.
        if not changed and self.data["resync_on_start"]:
            await self.async_resync()

    async def _async_tick(self, now: datetime) -> None:
        now = dt_util.as_local(now)
        if now.hour == 0 and now.minute == 0:
            await self._async_check_season(now.date())
        if not self.data["enabled"]:
            return
        weekday, minute = now.weekday(), now.hour * 60 + now.minute
        for schedule in self.active_schedules():
            try:
                action = engine.action_at(schedule, weekday, minute)
            except (KeyError, ValueError) as err:
                _LOGGER.warning("Horario %s no válido: %s", schedule.get("name"), err)
                continue
            if action:
                await self._async_apply(schedule, *action, reason="schedule")
        await self._async_check_presence(now)

    # ----------------------------------------------------------------- presence
    def _in_schedule(self, entity_id: str, weekday: int, minute: int) -> bool:
        return any(
            entity_id in s["entities"] and engine.active_slot(s, weekday, minute)
            for s in self.active_schedules()
        )

    def presence_status(self, rule: dict[str, Any]) -> tuple[bool | None, datetime | None]:
        """(somebody_there, empty_since). None when no sensor is usable."""
        valid = [
            st
            for sid in rule["sensors"]
            if (st := self.hass.states.get(sid)) is not None and st.state in ("on", "off")
        ]
        if not valid:
            return None, None
        if any(st.state == "on" for st in valid):
            return True, None
        return False, max(st.last_changed for st in valid)

    async def _async_check_presence(self, now: datetime) -> None:
        weekday, minute = now.weekday(), now.hour * 60 + now.minute
        for rule in self.data["presence_rules"]:
            if not rule.get("enabled", True):
                continue
            entity_id = rule["entity"]
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("off", STATE_UNAVAILABLE, STATE_UNKNOWN):
                continue
            present, empty_since = self.presence_status(rule)
            if present is not False or empty_since is None:
                continue
            # Grace period counts from whichever is later: room empty or AC turned on.
            since = max(empty_since, state.last_changed)
            if now - since < timedelta(minutes=rule["delay"]):
                continue
            in_schedule = self._in_schedule(entity_id, weekday, minute)
            if not engine.presence_rule_applies(rule, weekday, minute, in_schedule):
                continue
            _LOGGER.info("%s: sin presencia desde %s, se apaga", entity_id, empty_since)
            await self._async_apply_entity(entity_id, "off", None)
            self._record(entity_id, "Presencia", "off", None, "presence")

    async def async_save_presence_rule(self, rule: dict[str, Any]) -> None:
        rules = [r for r in self.data["presence_rules"] if r["entity"] != rule["entity"]]
        rules.append(rule)
        self.data["presence_rules"] = rules
        self._changed()

    async def async_delete_presence_rule(self, entity_id: str) -> None:
        self.data["presence_rules"] = [
            r for r in self.data["presence_rules"] if r["entity"] != entity_id
        ]
        self._changed()

    # ------------------------------------------------------------------ seasons
    async def _async_check_season(self, today: date) -> bool:
        """Apply the date-based season if a new boundary was reached."""
        if not self.data["auto_season"]:
            return False
        boundary = engine.season_boundary(self.data["season_dates"], today)
        if boundary is None:
            return False
        key = f"{boundary[0].isoformat()}:{boundary[1]}"
        if key == self.data.get("last_boundary"):
            return False
        self.data["last_boundary"] = key
        if boundary[1] == self.data["season"]:
            self._changed()
            return False
        _LOGGER.info("Cambio de temporada por fecha: %s", boundary[1])
        await self.async_set_season(boundary[1])
        return True

    async def async_set_season(self, season: str) -> None:
        if season == self.data["season"]:
            return
        stale_entities = self._entities_left_on()
        self.data["season"] = season
        self._changed()
        await self.async_resync()
        await self._async_turn_off_stale(stale_entities)

    def _entities_left_on(self) -> set[str]:
        """Entities the current season's schedules have switched on.

        An entity counts when one of its schedules has a slot running right
        now, or when the planner's last action on it was turning it on from one
        of these schedules (a point action with no end time). Entities the user
        switched on by hand are left alone.
        """
        now = dt_util.now()
        weekday, minute = now.weekday(), now.hour * 60 + now.minute
        result: set[str] = set()
        for schedule in self.active_schedules():
            try:
                running = engine.active_slot(schedule, weekday, minute) is not None
            except (KeyError, ValueError):
                running = False
            for entity_id in schedule["entities"]:
                last = self.last_actions.get(entity_id) or {}
                if running or (
                    last.get("action") == "apply"
                    and last.get("schedule") == schedule["name"]
                ):
                    result.add(entity_id)
        return result

    async def _async_turn_off_stale(self, entities: set[str]) -> None:
        """Turn off entities the previous season left running but the new one
        doesn't currently claim (e.g. the new season's schedules are all
        point actions with no end time, so resync alone never turns them off).
        """
        if not self.data["enabled"] or not entities:
            return
        now = dt_util.now()
        weekday, minute = now.weekday(), now.hour * 60 + now.minute
        claimed = {
            e
            for s in self.active_schedules()
            for e in s["entities"]
            if engine.active_slot(s, weekday, minute) is not None
        }
        for entity_id in entities - claimed:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state == "off":
                continue
            _LOGGER.info("%s: encendido por la temporada anterior, se apaga", entity_id)
            await self._async_apply_entity(entity_id, "off", None)
            self._record(entity_id, "Cambio de temporada", "off", None, "season_change")

    async def async_update_settings(self, **settings: Any) -> None:
        if "season_dates" in settings:
            self.data["season_dates"] = settings["season_dates"]
            self.data["last_boundary"] = None
        if "resync_on_start" in settings:
            self.data["resync_on_start"] = settings["resync_on_start"]
        if "auto_season" in settings:
            turned_on = settings["auto_season"] and not self.data["auto_season"]
            self.data["auto_season"] = settings["auto_season"]
            if turned_on:
                self.data["last_boundary"] = None
        if "enabled" in settings:
            turned_on = settings["enabled"] and not self.data["enabled"]
            self.data["enabled"] = settings["enabled"]
            if turned_on:
                self._changed()
                await self.async_resync()
        if "season" in settings:
            await self.async_set_season(settings["season"])
        self._changed()
        await self._async_check_season(dt_util.now().date())

    # ---------------------------------------------------------------- schedules
    def active_schedules(self) -> list[dict[str, Any]]:
        season = self.data["season"]
        return [
            s for s in self.data["schedules"] if s.get("enabled") and season in s["seasons"]
        ]

    async def async_save_schedule(self, schedule: dict[str, Any]) -> str:
        if not schedule.get("id"):
            schedule["id"] = uuid.uuid4().hex
        schedules = self.data["schedules"]
        for idx, existing in enumerate(schedules):
            if existing["id"] == schedule["id"]:
                schedules[idx] = schedule
                break
        else:
            schedules.append(schedule)
        self._changed()
        return schedule["id"]

    async def async_delete_schedule(self, schedule_id: str) -> None:
        self.data["schedules"] = [
            s for s in self.data["schedules"] if s["id"] != schedule_id
        ]
        self._changed()

    async def async_resync(self, schedule_id: str | None = None) -> None:
        """Force entities to the state the active schedules expect right now."""
        if not self.data["enabled"]:
            return
        now = dt_util.now()
        weekday, minute = now.weekday(), now.hour * 60 + now.minute
        for schedule in self.active_schedules():
            if schedule_id and schedule["id"] != schedule_id:
                continue
            target = engine.desired_state(schedule, weekday, minute)
            if target:
                await self._async_apply(schedule, *target, reason="resync")

    # ------------------------------------------------------------------ actions
    async def _async_apply(
        self, schedule: dict[str, Any], kind: str, slot: dict | None, *, reason: str
    ) -> None:
        for entity_id in schedule["entities"]:
            await self._async_apply_entity(entity_id, kind, slot)
            self._record(entity_id, schedule["name"], kind, slot, reason)

    @callback
    def _record(
        self, entity_id: str, source: str, kind: str, slot: dict | None, reason: str
    ) -> None:
        self.last_actions[entity_id] = {
            "time": dt_util.now().isoformat(),
            "schedule": source,
            "action": kind,
            "hvac_mode": slot.get("hvac_mode") if slot else "off",
            "temperature": slot.get("temperature") if slot else None,
            "reason": reason,
        }
        self.hass.bus.async_fire(
            EVENT_ACTION, {"entity_id": entity_id, **self.last_actions[entity_id]}
        )

    async def _async_apply_entity(
        self, entity_id: str, kind: str, slot: dict | None
    ) -> None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.warning("%s no está disponible; se omite la acción", entity_id)
            return
        hvac_modes = state.attributes.get("hvac_modes") or []
        target = {"entity_id": entity_id}
        try:
            mode = "off" if kind == "off" else (slot or {}).get("hvac_mode")
            if mode == "off":
                if "off" in hvac_modes:
                    await self._call("set_hvac_mode", {**target, "hvac_mode": "off"})
                else:
                    await self._call("turn_off", target)
                return
            if mode:
                if hvac_modes and mode not in hvac_modes:
                    _LOGGER.warning("%s no admite el modo %s", entity_id, mode)
                else:
                    await self._call("set_hvac_mode", {**target, "hvac_mode": mode})
            temperature = (slot or {}).get("temperature")
            if temperature is not None and mode not in ("fan_only", "dry"):
                await self._call("set_temperature", {**target, "temperature": temperature})
            fan_mode = (slot or {}).get("fan_mode")
            if fan_mode:
                await self._call("set_fan_mode", {**target, "fan_mode": fan_mode})
        except Exception as err:  # noqa: BLE001 - one bad device must not stop the rest
            _LOGGER.warning("Error aplicando horario a %s: %s", entity_id, err)

    async def _call(self, service: str, data: dict[str, Any]) -> None:
        await self.hass.services.async_call("climate", service, data, blocking=True)
