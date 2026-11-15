"""Constants for Climate Planner."""

DOMAIN = "climate_planner"
VERSION = "0.1.0"

STORAGE_KEY = f"{DOMAIN}.data"
STORAGE_VERSION = 1

SIGNAL_UPDATE = f"{DOMAIN}_update"
EVENT_ACTION = f"{DOMAIN}_action"

SEASON_SUMMER = "summer"
SEASON_WINTER = "winter"
SEASON_TRANSITION = "transition"
SEASONS = (SEASON_WINTER, SEASON_TRANSITION, SEASON_SUMMER)

PANEL_PATH = "climate-planner"
PANEL_COMPONENT = "climate-planner-panel"
STATIC_URL = "/climate_planner_static"

DEFAULT_SEASON_DATES = [
    {"season": SEASON_TRANSITION, "start": "04-01"},
    {"season": SEASON_SUMMER, "start": "06-15"},
    {"season": SEASON_TRANSITION, "start": "09-15"},
    {"season": SEASON_WINTER, "start": "11-01"},
]


def default_data() -> dict:
    """Return a fresh default storage payload."""
    return {
        "enabled": True,
        "season": SEASON_WINTER,
        "auto_season": True,
        "resync_on_start": True,
        "season_dates": [dict(d) for d in DEFAULT_SEASON_DATES],
        "last_boundary": None,
        "schedules": [],
    }
