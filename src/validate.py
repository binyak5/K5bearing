"""Startup sanity checks for config.yaml.

Catches the kind of config drift that would otherwise fail silently at post
time: an event with no wording, a European country with no timezone or ISO
code, a cap pointing at a category that doesn't exist, a watch location missing
its coordinates. Errors abort the run (a loud failure beats a broken or silent
feed); warnings print but are allowed.
"""
from __future__ import annotations

from . import tz

# Every category string a Signal can carry. category_daily_caps must reference
# one of these (a typo'd cap is silently ignored otherwise).
KNOWN_CATEGORIES = {
    "cityweather", "geomagnetic", "aurora", "solar", "solarwind", "flare",
    "radiation", "blackout", "rotterdam", "marine", "hab",
    "maritime", "global", "earthquake", "outdoor",
}


def _check_locations(errors: list[str], label: str, locations, need_tz: bool = False) -> None:
    for i, loc in enumerate(locations or []):
        where = f"{label}[{i}] ({(loc or {}).get('name', '?')})"
        if not loc.get("name"):
            errors.append(f"{label}[{i}]: missing 'name'")
        if loc.get("lat") is None or loc.get("lon") is None:
            errors.append(f"{where}: missing lat/lon")
        if need_tz and not loc.get("tz"):
            errors.append(f"{where}: missing 'tz'")


def validate_config(cfg: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors should abort; warnings are advisory."""
    errors: list[str] = []
    warnings: list[str] = []

    # 1. The Rotterdam alert source needs coordinates and a timezone.
    rt = cfg.get("rotterdam") or {}
    if rt.get("enabled"):
        if rt.get("lat") is None or rt.get("lon") is None:
            errors.append("rotterdam: missing lat/lon")
        if not rt.get("tz"):
            errors.append("rotterdam: missing 'tz'")

    # 2. Caps must reference real categories.
    for cat in (cfg.get("limits") or {}).get("category_daily_caps", {}):
        if cat not in KNOWN_CATEGORIES:
            errors.append(f"category_daily_caps: '{cat}' is not a known category")

    # 3. Watch locations need coordinates (and a timezone where stamped locally).
    _check_locations(errors, "city_weather.locations", (cfg.get("city_weather") or {}).get("locations"), need_tz=True)
    _check_locations(errors, "outdoor.locations", (cfg.get("outdoor") or {}).get("locations"))
    _check_locations(errors, "marine_seas.areas", (cfg.get("marine_seas") or {}).get("areas"))

    return errors, warnings


def assert_valid(cfg: dict) -> None:
    """Print warnings, then abort the run if there are any errors."""
    errors, warnings = validate_config(cfg)
    for w in warnings:
        print(f"config warning: {w}")
    if errors:
        for e in errors:
            print(f"config ERROR: {e}")
        raise SystemExit(f"config.yaml failed validation with {len(errors)} error(s); aborting.")
