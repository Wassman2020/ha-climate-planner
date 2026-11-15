"""Websocket API used by the side panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .schema import PRESENCE_SCHEMA, SCHEDULE_SCHEMA, SETTINGS_SCHEMA


def _planner(hass: HomeAssistant, connection, msg) -> Any:
    planner = hass.data.get(DOMAIN, {}).get("planner")
    if planner is None:
        connection.send_error(msg["id"], "not_loaded", "Climate Planner no está cargado")
    return planner


@callback
def async_register(hass: HomeAssistant) -> None:
    for handler in (
        ws_get,
        ws_save_schedule,
        ws_delete_schedule,
        ws_settings,
        ws_resync,
        ws_save_presence,
        ws_delete_presence,
    ):
        websocket_api.async_register_command(hass, handler)


@websocket_api.websocket_command({vol.Required("type"): "climate_planner/get"})
@websocket_api.require_admin
@callback
def ws_get(hass: HomeAssistant, connection, msg) -> None:
    if planner := _planner(hass, connection, msg):
        connection.send_result(msg["id"], planner.as_dict())


@websocket_api.websocket_command(
    {
        vol.Required("type"): "climate_planner/schedule/save",
        vol.Required("schedule"): dict,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_save_schedule(hass: HomeAssistant, connection, msg) -> None:
    if not (planner := _planner(hass, connection, msg)):
        return
    try:
        schedule = SCHEDULE_SCHEMA(msg["schedule"])
    except vol.Invalid as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    schedule_id = await planner.async_save_schedule(schedule)
    connection.send_result(msg["id"], {"id": schedule_id, **planner.as_dict()})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "climate_planner/schedule/delete",
        vol.Required("schedule_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_delete_schedule(hass: HomeAssistant, connection, msg) -> None:
    if planner := _planner(hass, connection, msg):
        await planner.async_delete_schedule(msg["schedule_id"])
        connection.send_result(msg["id"], planner.as_dict())


@websocket_api.websocket_command(
    {vol.Required("type"): "climate_planner/settings", **SETTINGS_SCHEMA}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_settings(hass: HomeAssistant, connection, msg) -> None:
    if planner := _planner(hass, connection, msg):
        settings = {k: v for k, v in msg.items() if k not in ("id", "type")}
        await planner.async_update_settings(**settings)
        connection.send_result(msg["id"], planner.as_dict())


@websocket_api.websocket_command(
    {
        vol.Required("type"): "climate_planner/resync",
        vol.Optional("schedule_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_resync(hass: HomeAssistant, connection, msg) -> None:
    if planner := _planner(hass, connection, msg):
        await planner.async_resync(msg.get("schedule_id"))
        connection.send_result(msg["id"], planner.as_dict())


@websocket_api.websocket_command(
    {vol.Required("type"): "climate_planner/presence/save", vol.Required("rule"): dict}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_save_presence(hass: HomeAssistant, connection, msg) -> None:
    if not (planner := _planner(hass, connection, msg)):
        return
    try:
        rule = PRESENCE_SCHEMA(msg["rule"])
    except vol.Invalid as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    await planner.async_save_presence_rule(rule)
    connection.send_result(msg["id"], planner.as_dict())


@websocket_api.websocket_command(
    {vol.Required("type"): "climate_planner/presence/delete", vol.Required("entity"): str}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_delete_presence(hass: HomeAssistant, connection, msg) -> None:
    if planner := _planner(hass, connection, msg):
        await planner.async_delete_presence_rule(msg["entity"])
        connection.send_result(msg["id"], planner.as_dict())
