"""Validation schemas for data coming from the panel / services."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.helpers import config_validation as cv

from . import engine
from .const import SEASONS


def _time(value: Any) -> str:
    if not isinstance(value, str):
        raise vol.Invalid("La hora debe ser un texto HH:MM")
    try:
        minutes = engine.parse_hm(value)
    except ValueError as err:
        raise vol.Invalid(str(err)) from err
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _month_day(value: Any) -> str:
    if not isinstance(value, str):
        raise vol.Invalid("La fecha debe ser un texto MM-DD")
    try:
        month, day = engine.parse_md(value)
    except ValueError as err:
        raise vol.Invalid(str(err)) from err
    return f"{month:02d}-{day:02d}"


def _check_slot(slot: dict) -> dict:
    try:
        engine.validate_slot(slot)
    except ValueError as err:
        raise vol.Invalid(str(err)) from err
    slot["days"] = sorted(set(slot["days"]))
    slot["end"] = slot["end"] or None
    return slot


SLOT_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required("days"): [vol.All(vol.Coerce(int), vol.Range(min=0, max=6))],
            vol.Required("start"): _time,
            vol.Optional("end", default=None): vol.Any(None, "", _time),
            vol.Optional("hvac_mode", default=None): vol.Any(None, cv.string),
            vol.Optional("temperature", default=None): vol.Any(
                None, vol.All(vol.Coerce(float), vol.Range(min=-20, max=90))
            ),
            vol.Optional("fan_mode", default=None): vol.Any(None, cv.string),
        },
        extra=vol.REMOVE_EXTRA,
    ),
    _check_slot,
)

def _legacy_season(value: Any) -> Any:
    if isinstance(value, dict) and "season" in value and "seasons" not in value:
        value = {**value, "seasons": [value["season"]]}
    return value


def _unique(value: list) -> list:
    return [s for s in SEASONS if s in value]


SCHEDULE_FIELDS = {
        vol.Optional("id"): vol.Any(None, cv.string),
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=80)),
        vol.Required("seasons"): vol.All(
            cv.ensure_list, [vol.In(SEASONS)], vol.Length(min=1), _unique
        ),
        vol.Optional("enabled", default=True): cv.boolean,
        vol.Optional("off_outside", default=True): cv.boolean,
        vol.Required("entities"): vol.All(
            cv.ensure_list, [cv.entity_domain("climate")], vol.Length(min=1)
        ),
        vol.Required("slots"): [SLOT_SCHEMA],
}

SCHEDULE_SCHEMA = vol.All(
    _legacy_season, vol.Schema(SCHEDULE_FIELDS, extra=vol.REMOVE_EXTRA)
)

def _check_window(window: dict) -> dict:
    if engine.parse_hm(window["start"]) % 1440 == engine.parse_hm(window["end"]) % 1440:
        raise vol.Invalid("La hora de inicio y la de fin no pueden ser iguales")
    window["days"] = sorted(set(window["days"]))
    return window


WINDOW_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required("days"): vol.All(
                [vol.All(vol.Coerce(int), vol.Range(min=0, max=6))], vol.Length(min=1)
            ),
            vol.Required("start"): _time,
            vol.Required("end"): _time,
        },
        extra=vol.REMOVE_EXTRA,
    ),
    _check_window,
)


def _check_presence(rule: dict) -> dict:
    if rule["mode"] == "windows" and not rule["windows"]:
        raise vol.Invalid("Añade al menos una franja horaria")
    return rule


PRESENCE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required("entity"): cv.entity_domain("climate"),
            vol.Required("sensors"): vol.All(
                cv.ensure_list, [cv.entity_id], vol.Length(min=1)
            ),
            vol.Optional("delay", default=15): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=720)
            ),
            vol.Optional("mode", default="always"): vol.In(engine.PRESENCE_MODES),
            vol.Optional("windows", default=list): [WINDOW_SCHEMA],
            vol.Optional("enabled", default=True): cv.boolean,
        },
        extra=vol.REMOVE_EXTRA,
    ),
    _check_presence,
)

SEASON_DATE_SCHEMA = vol.Schema(
    {
        vol.Required("season"): vol.In(SEASONS),
        vol.Required("start"): _month_day,
    },
    extra=vol.REMOVE_EXTRA,
)

SETTINGS_SCHEMA = {
    vol.Optional("season"): vol.In(SEASONS),
    vol.Optional("enabled"): cv.boolean,
    vol.Optional("auto_season"): cv.boolean,
    vol.Optional("resync_on_start"): cv.boolean,
    vol.Optional("season_dates"): vol.All([SEASON_DATE_SCHEMA], vol.Length(min=1)),
}
