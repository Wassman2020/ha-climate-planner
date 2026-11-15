from datetime import date

from custom_components.climate_planner import engine

MON, TUE, SUN = 0, 1, 6
m = engine.parse_hm


def sched(*slots, off_outside=True):
    return {"slots": list(slots), "off_outside": off_outside}


DAY = {"days": [0, 1, 2, 3, 4], "start": "07:00", "end": "09:00", "hvac_mode": "heat", "temperature": 21}
NIGHT = {"days": [SUN], "start": "22:00", "end": "06:00", "hvac_mode": "heat", "temperature": 18}
MIDNIGHT = {"days": [MON], "start": "20:00", "end": "00:00", "hvac_mode": "cool", "temperature": 25}


def test_start_and_end():
    s = sched(DAY)
    assert engine.action_at(s, MON, m("07:00")) == ("apply", DAY)
    assert engine.action_at(s, MON, m("08:00")) is None
    assert engine.action_at(s, MON, m("09:00")) == ("off", None)
    assert engine.action_at(s, SUN, m("07:00")) is None


def test_no_off_when_disabled():
    assert engine.action_at(sched(DAY, off_outside=False), MON, m("09:00")) is None


def test_overnight_slot():
    s = sched(NIGHT)
    assert engine.action_at(s, SUN, m("22:00")) == ("apply", NIGHT)
    assert engine.action_at(s, MON, m("06:00")) == ("off", None)
    assert engine.action_at(s, SUN, m("06:00")) is None
    assert engine.active_slot(s, MON, m("03:00")) is NIGHT
    assert engine.active_slot(s, MON, m("07:00")) is None


def test_end_at_midnight():
    s = sched(MIDNIGHT)
    assert engine.action_at(s, TUE, 0) == ("off", None)
    assert engine.active_slot(s, MON, m("23:59")) is MIDNIGHT
    assert engine.parse_hm("24:00") == 1440


def test_back_to_back_slots_do_not_turn_off():
    a = {**DAY, "end": "09:00"}
    b = {**DAY, "start": "09:00", "end": "12:00", "temperature": 19}
    assert engine.action_at(sched(a, b), MON, m("09:00")) == ("apply", b)


def test_desired_state():
    s = sched(DAY)
    assert engine.desired_state(s, MON, m("08:30")) == ("apply", DAY)
    assert engine.desired_state(s, MON, m("10:00")) == ("off", None)
    assert engine.desired_state(sched(DAY, off_outside=False), MON, m("10:00")) is None


def test_season_boundary():
    dates = [
        {"season": "transition", "start": "04-01"},
        {"season": "summer", "start": "06-15"},
        {"season": "transition", "start": "09-15"},
        {"season": "winter", "start": "11-01"},
    ]
    assert engine.season_boundary(dates, date(2026, 11, 15)) == (date(2026, 11, 1), "winter")
    assert engine.season_boundary(dates, date(2027, 2, 1)) == (date(2026, 11, 1), "winter")
    assert engine.season_boundary(dates, date(2027, 4, 1)) == (date(2027, 4, 1), "transition")
    assert engine.season_boundary(dates, date(2027, 7, 1))[1] == "summer"


def test_validation():
    import pytest
    with pytest.raises(ValueError):
        engine.validate_slot({**DAY, "end": "07:00"})
    with pytest.raises(ValueError):
        engine.parse_hm("25:00")
    with pytest.raises(ValueError):
        engine.parse_md("02-30")
    assert engine.parse_md("02-29") == (2, 29)


def test_point_actions():
    off23 = {"days": [0, 1, 2, 3], "start": "23:00", "end": None, "hvac_mode": "off"}
    heat = {"days": [0, 1, 2, 3], "start": "20:00", "end": "22:30", "hvac_mode": "heat", "temperature": 22}
    s = sched(heat, off23)
    engine.validate_slot(off23)
    assert engine.action_at(s, MON, m("23:00")) == ("off", None)
    assert engine.action_at(s, MON, m("22:30")) == ("off", None)
    assert engine.active_slot(s, MON, m("23:00")) is None
    assert engine.desired_state(s, MON, m("21:00")) == ("apply", heat)
    # real slot wins over an off point at the same minute
    on23 = {**heat, "start": "23:00", "end": "23:30"}
    assert engine.action_at(sched(off23, on23), MON, m("23:00")) == ("apply", on23)


def test_resync_ignores_point_only_schedules():
    off = {"days": [0, 1, 2, 3, 4, 5, 6], "start": "02:00", "end": None, "hvac_mode": "off"}
    assert engine.desired_state(sched(off), MON, m("10:00")) is None


def test_presence_applies():
    w = {"mode": "windows", "windows": [{"days": [0], "start": "22:00", "end": "02:00"}]}
    assert engine.presence_rule_applies(w, MON, m("23:00"), False)
    assert engine.presence_rule_applies(w, TUE, m("01:00"), False)
    assert not engine.presence_rule_applies(w, TUE, m("03:00"), False)
    assert engine.presence_rule_applies({"mode": "outside"}, MON, 0, False)
    assert not engine.presence_rule_applies({"mode": "outside"}, MON, 0, True)
    assert engine.presence_rule_applies({"mode": "always"}, MON, 0, True)
