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


async def test_services_multi_season(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    await hass.config.async_set_time_zone("Europe/Madrid")
    tz = dt_util.get_time_zone("Europe/Madrid")
    freezer.move_to(dt_util.as_utc(datetime(2026, 11, 16, 22, 59, 0, tzinfo=tz)))
    hass.states.async_set("climate.sotano", "heat", {"hvac_modes": ["off", "heat"]})
    hvac = async_mock_service(hass, "climate", "set_hvac_mode")
    await _setup(hass)
    res = await hass.services.async_call(DOMAIN, "save_schedule", {
        "id": "sotano_seguridad", "name": "Sótano apagados", "seasons": ["summer", "winter", "transition", "winter"],
        "entities": "climate.sotano", "off_outside": False,
        "slots": [{"days": [0, 1, 2, 3, 4, 5, 6], "start": t} for t in ("01:00", "23:00")],
    }, blocking=True, return_response=True)
    assert res == {"id": "sotano_seguridad"}
    data = await hass.services.async_call(DOMAIN, "list_schedules", {}, blocking=True, return_response=True)
    sch = data["schedules"][0]
    assert sch["seasons"] == ["winter", "transition", "summer"]
    assert sch["slots"][0]["end"] is None
    freezer.tick(60)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hvac[-1].data == {"entity_id": "climate.sotano", "hvac_mode": "off"}
    await hass.services.async_call(DOMAIN, "delete_schedule", {"schedule_id": "sotano_seguridad"}, blocking=True)
    data = await hass.services.async_call(DOMAIN, "list_schedules", {}, blocking=True, return_response=True)
    assert data["schedules"] == []


async def test_presence_rules(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    await hass.config.async_set_time_zone("Europe/Madrid")
    tz = dt_util.get_time_zone("Europe/Madrid")
    at = lambda d, h, mi: dt_util.as_utc(datetime(2026, 11, d, h, mi, 0, tzinfo=tz))
    freezer.move_to(at(16, 10, 0))  # Monday
    hass.states.async_set("climate.salon", "heat", {"hvac_modes": ["off", "heat"]})
    hass.states.async_set("binary_sensor.radar", "on")
    hass.states.async_set("binary_sensor.cam", "unavailable")
    hvac = async_mock_service(hass, "climate", "set_hvac_mode")
    await _setup(hass)
    planner = hass.data[DOMAIN]["planner"]

    async def minute(h, mi):
        freezer.move_to(at(16, h, mi))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    # Schedule 16:00-23:00 heat; rule only outside schedules, 10 min
    await hass.services.async_call(DOMAIN, "save_schedule", {
        "id": "s", "name": "Salón", "seasons": ["winter"], "entities": ["climate.salon"],
        "slots": [{"days": [0], "start": "16:00", "end": "23:00", "hvac_mode": "heat", "temperature": 22}],
    }, blocking=True)
    await hass.services.async_call(DOMAIN, "save_presence_rule", {
        "entity": "climate.salon", "sensors": ["binary_sensor.radar", "binary_sensor.cam"],
        "delay": 10, "mode": "outside"}, blocking=True)

    hass.states.async_set("binary_sensor.radar", "off")  # empty from 10:00
    await minute(10, 5)
    assert not hvac  # delay not reached
    await minute(10, 10)
    assert hvac[-1].data["hvac_mode"] == "off"

    # inside schedule: no presence-off
    hvac.clear()
    freezer.move_to(at(16, 17, 0))
    hass.states.async_set("climate.salon", "cool", {"hvac_modes": ["off", "heat", "cool"]})
    hass.states.async_set("binary_sensor.radar", "on")
    hass.states.async_set("binary_sensor.radar", "off")
    await minute(17, 30)
    assert not hvac

    # windows mode: 17:00-18:00 -> fires
    await hass.services.async_call(DOMAIN, "save_presence_rule", {
        "entity": "climate.salon", "sensors": ["binary_sensor.radar"], "delay": 10,
        "mode": "windows", "windows": [{"days": [0], "start": "17:00", "end": "18:00"}]}, blocking=True)
    await minute(17, 31)
    assert hvac[-1].data["hvac_mode"] == "off"
    assert planner.last_actions["climate.salon"]["reason"] == "presence"
    assert len(planner.data["presence_rules"]) == 1

    # someone present -> nothing; only unavailable sensors -> nothing
    hvac.clear()
    hass.states.async_set("binary_sensor.radar", "on")
    await minute(17, 50)
    hass.states.async_set("binary_sensor.radar", "unavailable")
    await minute(17, 59)
    assert not hvac
    await hass.services.async_call(DOMAIN, "delete_presence_rule", {"entity": "climate.salon"}, blocking=True)
    assert planner.data["presence_rules"] == []


async def test_season_change_turns_off_previous_season(hass: HomeAssistant, freezer: FrozenDateTimeFactory):
    """Switching to a season whose schedules have no end times must still turn
    off what the previous season switched on, and leave everything else alone."""
    await hass.config.async_set_time_zone("Europe/Madrid")
    tz = dt_util.get_time_zone("Europe/Madrid")
    freezer.move_to(dt_util.as_utc(datetime(2026, 11, 15, 19, 59, 0, tzinfo=tz)))  # Sunday
    modes = {"hvac_modes": ["off", "heat", "cool"]}
    hass.states.async_set("climate.aitor", "off", modes)
    hass.states.async_set("climate.cocina", "off", modes)
    hvac = async_mock_service(hass, "climate", "set_hvac_mode")
    async_mock_service(hass, "climate", "set_temperature")
    await _setup(hass)
    await hass.services.async_call(DOMAIN, "save_schedule", {
        "id": "w", "name": "Invierno", "seasons": ["winter"],
        "entities": ["climate.aitor", "climate.cocina"],
        "slots": [{"days": [6], "start": "20:00", "end": "22:30", "hvac_mode": "heat", "temperature": 21}],
    }, blocking=True)
    await hass.services.async_call(DOMAIN, "save_schedule", {
        "id": "t", "name": "Entretiempo", "seasons": ["transition"], "entities": ["climate.aitor"],
        "slots": [{"days": [6], "start": "23:00"}],
    }, blocking=True)

    freezer.tick(60)  # 20:00 -> winter slot starts
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert [c.data["entity_id"] for c in hvac] == ["climate.aitor", "climate.cocina"]
    hass.states.async_set("climate.aitor", "heat", modes)
    hass.states.async_set("climate.cocina", "off", modes)  # already off: no extra call

    hvac.clear()
    await hass.services.async_call(DOMAIN, "set_season", {"season": "transition"}, blocking=True)
    await hass.async_block_till_done()
    assert [c.data for c in hvac] == [{"entity_id": "climate.aitor", "hvac_mode": "off"}]
    assert hass.data[DOMAIN]["planner"].last_actions["climate.aitor"]["reason"] == "season_change"

    # Switching back while nothing of the leaving season runs turns nothing off.
    hass.states.async_set("climate.aitor", "heat", modes)  # turned on by hand
    hvac.clear()
    await hass.services.async_call(DOMAIN, "set_season", {"season": "summer"}, blocking=True)
    await hass.async_block_till_done()
    assert not hvac
