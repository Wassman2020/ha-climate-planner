"""Master switch and automatic season switch."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import PlannerEntity

ICONS = {"enabled": "mdi:calendar-clock", "auto_season": "mdi:calendar-sync"}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    planner = hass.data[DOMAIN]["planner"]
    async_add_entities(PlannerSwitch(planner, key) for key in ICONS)


class PlannerSwitch(PlannerEntity, SwitchEntity):
    def __init__(self, planner, key: str) -> None:
        super().__init__(planner, key)
        self._key = key
        self._attr_icon = ICONS[key]

    @property
    def is_on(self) -> bool:
        return bool(self.planner.data[self._key])

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.planner.async_update_settings(**{self._key: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.planner.async_update_settings(**{self._key: False})
