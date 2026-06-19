"""Startup sanity checks for config.yaml.

Catches the kind of config drift that would otherwise fail silently at post
time: an event with no wording, a European country with no timezone or ISO
code, a cap pointing at a category that doesn't exist, a watch location missing
its coordinates. Errors abort the run (a loud failure beats a broken or silent
feed); warnings print but are allowed.
"""
from __future__ import annotations

from . import tz
from .sources import nws

# Every category string a Signal can carry. category_daily_caps must reference
# one of these (a typo'd cap is silently ignored otherwise).
KNOWN_CATEGORIES = {
    "cityweather", "geomagnetic", "aurora", "solar", "solarwind", "flare",
    "radiation", "blackout", "weather", "weather_eu", "marine", "hab",
    "maritime", "global", "earthquake", "gulf", "outdoor",
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

    # 1. US events <-> wording. Every posted event needs an ACTIONS entry.
    #    Small Craft Advisory is the exception: it only ever posts as the
    #    collapsed roundup, never individually, so it has no ACTIONS line.
    events = (cfg.get("weather") or {}).get("events", [])
    for ev in events:
        if ev == "Small Craft Advisory":
            continue
        if ev not in nws.ACTIONS:
            errors.append(f"weather.events: '{ev}' has no wording in nws.ACTIONS")
    for ev in nws.ACTIONS:
        if ev not in events:
            warnings.append(f"nws.ACTIONS: '{ev}' is never posted (not in weather.events)")

    # 2. European countries need both a timezone and an ISO code, or their posts
    #    lose the local timestamp / country prefix.
    for c in (cfg.get("weather_eu") or {}).get("countries", []):
        if tz.zone_for_country(c) is None:
            errors.append(f"weather_eu.countries: '{c}' has no timezone in tz.COUNTRY_ZONES")
        if tz.code_for_country(c) is None:
            errors.append(f"weather_eu.countries: '{c}' has no ISO code in tz.COUNTRY_CODES")

    # 3. Caps must reference real categories.
    for cat in (cfg.get("limits") or {}).get("category_daily_caps", {}):
        if cat not in KNOWN_CATEGORIES:
            errors.append(f"category_daily_caps: '{cat}' is not a known category")

    # 4. Watch locations need coordinates (and a timezone where stamped locally).
    _check_locations(errors, "gulf_weather.locations", (cfg.get("gulf_weather") or {}).get("locations"), need_tz=True)
    _check_locations(errors, "city_weather.locations", (cfg.get("city_weather") or {}).get("locations"), need_tz=True)
    _check_locations(errors, "outdoor.locations", (cfg.get("outdoor") or {}).get("locations"))
    _check_locations(errors, "marine_seas.areas", (cfg.get("marine_seas") or {}).get("areas"))

    # 5. Gulf cities derive their country code from the timezone; warn (not error)
    #    if a tz has no mapping, since the post would then show no country code.
    for loc in (cfg.get("gulf_weather") or {}).get("locations", []):
        z = loc.get("tz")
        if z and tz.code_for_zone(z) is None:
            warnings.append(
                f"gulf_weather: '{loc.get('name', '?')}' tz '{z}' has no ISO code in "
                "tz.ZONE_CODES (post will show no country after the time)"
            )

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
