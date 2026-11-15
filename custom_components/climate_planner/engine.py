"""Pure scheduling logic (no Home Assistant imports, easy to test).

Conventions
-----------
* Weekdays follow ``datetime.weekday()``: 0 = Monday ... 6 = Sunday.
* Times are "HH:MM" strings; "24:00" and "00:00" are accepted as an end of
  slot meaning midnight.
* A slot whose end is <= its start crosses midnight; its ``days`` refer to the
  day on which it *starts*.
"""

from __future__ import annotations

from datetime import date
from typing import Any

MINUTES_PER_DAY = 1440


def parse_hm(value: str) -> int:
    """Parse "HH:MM" into minutes since midnight (0..1440)."""
    try:
        hours, minutes = value.strip().split(":")
        h, m = int(hours), int(minutes)
    except (AttributeError, ValueError) as err:
        raise ValueError(f"Hora no válida: {value!r}") from err
    if not (0 <= h <= 24 and 0 <= m < 60) or (h == 24 and m != 0):
        raise ValueError(f"Hora no válida: {value!r}")
    return h * 60 + m


def parse_md(value: str) -> tuple[int, int]:
    """Parse "MM-DD" into (month, day)."""
    try:
        month, day = (int(p) for p in value.strip().split("-"))
    except (AttributeError, ValueError) as err:
        raise ValueError(f"Fecha no válida: {value!r}") from err
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        raise ValueError(f"Fecha no válida: {value!r}")
    # Validate against a leap year so 02-29 is allowed.
    try:
        date(2024, month, day)
    except ValueError as err:
        raise ValueError(f"Fecha no válida: {value!r}") from err
    return month, day


def _bounds(slot: dict[str, Any]) -> tuple[int, int, bool]:
    start = parse_hm(slot["start"]) % MINUTES_PER_DAY
    end = parse_hm(slot["end"]) % MINUTES_PER_DAY
    return start, end, end <= start


def validate_slot(slot: dict[str, Any]) -> None:
    """Raise ValueError if a slot is not usable."""
    start, end, _ = _bounds(slot)
    if start == end:
        raise ValueError("La hora de inicio y la de fin no pueden ser iguales")
    if not slot.get("days"):
        raise ValueError("Cada franja necesita al menos un día")


def slot_starts_at(slot: dict[str, Any], weekday: int, minute: int) -> bool:
    start, _, _ = _bounds(slot)
    return start == minute and weekday in slot["days"]


def slot_ends_at(slot: dict[str, Any], weekday: int, minute: int) -> bool:
    _, end, crosses = _bounds(slot)
    if end != minute:
        return False
    start_day = (weekday - 1) % 7 if crosses else weekday
    return start_day in slot["days"]


def minutes_into_slot(slot: dict[str, Any], weekday: int, minute: int) -> int | None:
    """Return how many minutes the slot has been running, or None if inactive."""
    start, end, crosses = _bounds(slot)
    days = slot["days"]
    if not crosses:
        if weekday in days and start <= minute < end:
            return minute - start
        return None
    if weekday in days and minute >= start:
        return minute - start
    if (weekday - 1) % 7 in days and minute < end:
        return MINUTES_PER_DAY - start + minute
    return None


def active_slot(schedule: dict[str, Any], weekday: int, minute: int) -> dict | None:
    """Return the slot active now; if several overlap, the most recently started."""
    best: tuple[int, dict] | None = None
    for slot in schedule.get("slots", []):
        running = minutes_into_slot(slot, weekday, minute)
        if running is not None and (best is None or running < best[0]):
            best = (running, slot)
    return best[1] if best else None


def action_at(
    schedule: dict[str, Any], weekday: int, minute: int
) -> tuple[str, dict | None] | None:
    """Return the event that fires exactly at this minute.

    ("apply", slot) when a slot starts, ("off", None) when a slot ends and
    nothing else is running, or None when nothing happens.
    """
    starting = [s for s in schedule.get("slots", []) if slot_starts_at(s, weekday, minute)]
    if starting:
        return ("apply", starting[-1])
    if not schedule.get("off_outside", True):
        return None
    if any(slot_ends_at(s, weekday, minute) for s in schedule.get("slots", [])):
        if active_slot(schedule, weekday, minute) is None:
            return ("off", None)
    return None


def desired_state(
    schedule: dict[str, Any], weekday: int, minute: int
) -> tuple[str, dict | None] | None:
    """Return what the entities *should* look like right now (for resync)."""
    slot = active_slot(schedule, weekday, minute)
    if slot is not None:
        return ("apply", slot)
    if schedule.get("off_outside", True):
        return ("off", None)
    return None


def _safe_date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError:  # 29 Feb on a non-leap year
        return date(year, month, day - 1)


def season_boundary(
    season_dates: list[dict[str, str]], today: date
) -> tuple[date, str] | None:
    """Return (date, season) of the latest season change on or before today."""
    best: tuple[date, str] | None = None
    for entry in season_dates:
        month, day = parse_md(entry["start"])
        candidate = _safe_date(today.year, month, day)
        if candidate > today:
            candidate = _safe_date(today.year - 1, month, day)
        if best is None or candidate > best[0]:
            best = (candidate, entry["season"])
    return best
