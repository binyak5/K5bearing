"""Gulf-state weather alerts the official feeds miss: extreme heat and shamal
winds. NWS is US-only and MeteoAlarm is Europe-only, so the Gulf has no severe-
weather warning feed here. We derive these from Open-Meteo (keyless) for a
watchlist of Gulf cities. Temperatures in °C, winds in km/h.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from ..config import USER_AGENT
from . import Signal, pick

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 20

HEAT_VARIANTS = [
    "Dangerous heat is gripping {name}, the temperature at {temp}°C and feeling like {feels}°C. Stay out of the midday sun, keep drinking water, and check on anyone living or working outdoors.",
    "Brutal heat has settled over {name}, {temp}°C and feeling like {feels}°C. Keep outdoor time to the early hours, stay hydrated, and watch closely for heat stress.",
]

# Winds out of the NW are the classic Gulf "shamal".
SHAMAL_VARIANTS = [
    "A shamal is blasting {name}, winds at {wind} km/h and gusting to {gust}. Expect blowing dust and dropping visibility. Secure loose objects and take care on exposed roads.",
    "Strong shamal winds are raking {name} at {wind} km/h, gusting to {gust}. Dust will cut visibility and rattle anything loose. Tie things down and drive with care.",
]

WIND_VARIANTS = [
    "Strong winds are raking {name} at {wind} km/h and gusting to {gust}. Expect blowing dust and reduced visibility. Secure loose objects and take care outdoors.",
    "A strong blow has set in over {name}, winds at {wind} km/h and gusts to {gust}. Watch for flying dust and poor visibility, and tie down anything loose.",
]


def _current(lat: float, lon: float) -> dict | None:
    try:
        resp = requests.get(
            FORECAST_URL,
            headers={"User-Agent": USER_AGENT},
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,wind_speed_10m,wind_gusts_10m,wind_direction_10m",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("current") or {}
    except (requests.RequestException, ValueError):
        return None


def gulf_signals(locations: list[dict], heat_feels_c: float, wind_gust_kmh: float) -> list[Signal]:
    signals: list[Signal] = []
    for loc in locations:
        name, lat, lon = loc.get("name"), loc.get("lat"), loc.get("lon")
        zone = loc.get("tz", "UTC")
        if name is None or lat is None or lon is None:
            continue
        cur = _current(lat, lon)
        if not cur:
            continue
        try:
            today = datetime.now(ZoneInfo(zone)).date().isoformat()
        except Exception:
            from datetime import timezone
            today = datetime.now(timezone.utc).date().isoformat()

        temp = cur.get("temperature_2m")
        feels = cur.get("apparent_temperature")
        ref = feels if feels is not None else temp
        if ref is not None and ref >= heat_feels_c:
            key = f"gulfheat:{name}:{today}"
            signals.append(
                Signal(
                    category="gulf",
                    severity=70,
                    text=pick(HEAT_VARIANTS, key).format(
                        name=name, temp=round(temp if temp is not None else ref), feels=round(ref)
                    ),
                    dedup_key=key,
                    hashtags=["#ExtremeHeat", "#Gulf"],
                    tz=zone,
                )
            )

        gust = cur.get("wind_gusts_10m")
        wind = cur.get("wind_speed_10m")
        direction = cur.get("wind_direction_10m")
        if gust is not None and gust >= wind_gust_kmh:
            is_shamal = direction is not None and 290 <= direction <= 340
            variants = SHAMAL_VARIANTS if is_shamal else WIND_VARIANTS
            key = f"gulfwind:{name}:{today}"
            signals.append(
                Signal(
                    category="gulf",
                    severity=68,
                    text=pick(variants, key).format(
                        name=name,
                        wind=round(wind) if wind is not None else round(gust),
                        gust=round(gust),
                    ),
                    dedup_key=key,
                    hashtags=["#Shamal", "#Gulf"],
                    tz=zone,
                )
            )
    return signals
