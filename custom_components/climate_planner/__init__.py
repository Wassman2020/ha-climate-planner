"""Climate Planner: weekly, season-aware schedules for any climate entity."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError

from . import websocket
from .const import DOMAIN, PANEL_COMPONENT, PANEL_PATH, SEASONS, STATIC_URL, VERSION
from .planner import Planner

PLATFORMS = [Platform.SELECT, Platform.SWITCH]

SERVICE_RESYNC = "resync"
SERVICE_SET_SEASON = "set_season"


def _get_planner(hass: HomeAssistant) -> Planner:
    planner = hass.data.get(DOMAIN, {}).get("planner")
    if planner is None:
        raise ServiceValidationError("Climate Planner no está cargado")
    return planner


async def _async_register_frontend(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get("static_registered"):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    STATIC_URL, str(Path(__file__).parent / "frontend"), False
                )
            ]
        )
        domain_data["static_registered"] = True
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title="Climatización",
        sidebar_icon="mdi:calendar-clock",
        module_url=f"{STATIC_URL}/climate-planner-panel.js?v={VERSION}",
        require_admin=True,
        config={},
    )


def _async_register_services(hass: HomeAssistant) -> None:
    async def resync(call: ServiceCall) -> None:
        await _get_planner(hass).async_resync()

    async def set_season(call: ServiceCall) -> None:
        await _get_planner(hass).async_update_settings(season=call.data["season"])

    hass.services.async_register(DOMAIN, SERVICE_RESYNC, resync)
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SEASON,
        set_season,
        schema=vol.Schema({vol.Required("season"): vol.In(SEASONS)}),
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    planner = Planner(hass, entry)
    await planner.async_load()

    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data["planner"] = planner
    if not domain_data.get("ws_registered"):
        websocket.async_register(hass)
        domain_data["ws_registered"] = True

    await _async_register_frontend(hass)
    _async_register_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    planner.start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        planner: Planner = hass.data[DOMAIN].pop("planner")
        planner.stop()
        await planner.async_flush()
        frontend.async_remove_panel(hass, PANEL_PATH)
        for service in (SERVICE_RESYNC, SERVICE_SET_SEASON):
            hass.services.async_remove(DOMAIN, service)
    return unloaded
