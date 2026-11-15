from datetime import datetime

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.climate_planner.const import DOMAIN


async def _setup(hass: HomeAssistant):
    await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_full_flow(hass: HomeAssistant, hass_ws_client, freezer: FrozenDateTimeFactory):
    ws = await hass_ws_client(hass)
    await hass.config.async_set_time_zone("Europe/Madrid")
    # Monday 2026-11-16 06:59:00 local
    freezer.move_to(dt_util.as_utc(datetime(2026, 11, 16, 6, 59, 0, tzinfo=dt_util.get_time_zone("Europe/Madrid"))))
    hass.states.async_set("climate.salon", "off", {"hvac_modes": ["off", "heat", "cool", "heat_cool"], "fan_modes": ["auto", "1"]})
    hvac = async_mock_service(hass, "climate", "set_hvac_mode")
    temp = async_mock_service(hass, "climate", "set_temperature")
    fan = async_mock_service(hass, "climate", "set_fan_mode")

    entry = await _setup(hass)
    assert hass.states.get("select.climate_planner_season").state == "winter"
    assert hass.states.get("switch.climate_planner_scheduling_enabled").state == "on"

    await ws.send_json({"id": 1, "type": "climate_planner/schedule/save", "schedule": {
        "name": "Salón invierno", "season": "winter", "entities": ["climate.salon"],
        "slots": [{"days": [0, 1, 2, 3, 4], "start": "7:00", "end": "09:00", "hvac_mode": "heat", "temperature": 21.5, "fan_mode": "auto"}],
    }})
    res = await ws.receive_json()
    assert res["success"], res
    assert res["result"]["schedules"][0]["slots"][0]["start"] == "07:00"

    # invalid schedule rejected
    await ws.send_json({"id": 2, "type": "climate_planner/schedule/save", "schedule": {
        "name": "x", "season": "winter", "entities": ["light.x"], "slots": []}})
    assert not (await ws.receive_json())["success"]

    freezer.tick(60)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert [c.data["hvac_mode"] for c in hvac] == ["heat"]
    assert temp[-1].data["temperature"] == 21.5
    assert fan[-1].data["fan_mode"] == "auto"

    freezer.move_to(dt_util.as_utc(datetime(2026, 11, 16, 9, 0, 0, tzinfo=dt_util.get_time_zone("Europe/Madrid"))))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hvac[-1].data["hvac_mode"] == "off"

    # season switch to summer: winter schedule no longer fires
    await hass.services.async_call("select", "select_option", {"entity_id": "select.climate_planner_season", "option": "summer"}, blocking=True)
    assert hass.states.get("select.climate_planner_season").state == "summer"
    n = len(hvac)
    freezer.move_to(dt_util.as_utc(datetime(2026, 11, 17, 7, 0, 0, tzinfo=dt_util.get_time_zone("Europe/Madrid"))))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(hvac) == n

    # reload keeps data
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    # (the test clock moved a day, so the ws auth token expired; check directly)
    data = hass.data[DOMAIN]["planner"].as_dict()
    assert data["season"] == "summer"
    assert len(data["schedules"]) == 1
    assert hass.states.get("select.climate_planner_season").state == "summer"

    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_panel_and_auto_season(hass: HomeAssistant, hass_client, freezer: FrozenDateTimeFactory):
    await hass.config.async_set_time_zone("Europe/Madrid")
    tz = dt_util.get_time_zone("Europe/Madrid")
    freezer.move_to(dt_util.as_utc(datetime(2027, 6, 14, 23, 59, 0, tzinfo=tz)))
    await _setup(hass)
    client = await hass_client()
    assert "climate-planner" in hass.data["frontend_panels"]
    resp = await client.get("/climate_planner_static/climate-planner-panel.js")
    assert resp.status == 200
    assert "climate-planner-panel" in await resp.text()

    assert hass.states.get("select.climate_planner_season").state == "transition"
    # manual override survives until next boundary
    await hass.services.async_call("climate_planner", "set_season", {"season": "winter"}, blocking=True)
    freezer.tick(60)  # 15 June 00:00 -> summer boundary
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get("select.climate_planner_season").state == "summer"
