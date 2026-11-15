"""Season selector."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SEASONS
from .entity import PlannerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([SeasonSelect(hass.data[DOMAIN]["planner"], "season")])


class SeasonSelect(PlannerEntity, SelectEntity):
    _attr_icon = "mdi:weather-partly-snowy-rainy"
    _attr_options = list(SEASONS)

    @property
    def current_option(self) -> str:
        return self.planner.data["season"]

    async def async_select_option(self, option: str) -> None:
        await self.planner.async_update_settings(season=option)
