"""Gulf-state weather alerts the official feeds miss: extreme heat, shamal
winds, dense fog, thunderstorms, heavy rain / flash flooding, and dust storms.
NWS is US-only and MeteoAlarm is Europe-only, so the Gulf has no severe-weather
warning feed here. We derive these from Open-Meteo (keyless) for a watchlist of
Gulf cities. Temperatures in °C, winds in km/h, visibility in metres.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from ..config import USER_AGENT
from .. import tz
from . import Signal, pick, gather

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEOUT = 20

# WMO weather codes for thunderstorms (slight/moderate, with hail).
THUNDER_CODES = {95, 96, 99}

HEAT_VARIANTS = [
    "Severe heat is gripping {name}, the temperature at {temp}°C and feeling like {feels}°C. Stay out of the midday sun, keep drinking water, and check on anyone living or working outdoors.",
    "Brutal heat has settled over {name}, {temp}°C and feeling like {feels}°C. Keep outdoor time to the early hours, stay hydrated, and watch closely for heat stress.",
]

# Winds out of the NW are the classic Gulf "shamal".
SHAMAL_VARIANTS = [
    "A shamal is blasting {name}, winds at {wind} km/h and gusting to {gust}. Expect blowing dust and dropping visibility. Secure loose objects and take care on exposed roads.",
    "Strong shamal winds are raking {name} at {wind} km/h, gusting to {gust}. Dust will cut visibility and rattle anything loose. Tie things down and drive with care.",
]

WIND_VARIANTS = [
    "A strong blow has set in over {name}, winds at {wind} km/h and gusts to {gust}. Expect blowing dust and reduced visibility. Secure loose objects and take care outdoors.",
]

FOG_VARIANTS = [
    "Dense fog has closed in over {name}, visibility down to about {vis} m. Slow right down, switch to low-beam headlights, and leave plenty of room on the road.",
    "Thick fog is blanketing {name} with visibility near {vis} m. Reduce speed, use dipped headlights, and watch for sudden slow or stopped traffic.",
]

THUNDER_VARIANTS = [
    "Thunderstorms are breaking out over {name}, with lightning, sudden downpours, and gusty winds. Head indoors away from windows and off exposed ground until they pass.",
    "A thunderstorm is rolling over {name}, bringing lightning and heavy rain. Get inside, stay clear of open areas, and hold off on driving until it moves through.",
]

RAIN_VARIANTS = [
    "Heavy rain is hammering {name} at about {rain} mm in the hour, and the hard ground sheds it fast. Avoid wadis and low crossings, and never drive through floodwater.",
    "Intense rainfall has hit {name}, around {rain} mm in the hour. Flash flooding can come quickly off the dry ground. Steer clear of low-lying roads and wadis.",
]

DUST_VARIANTS = [
    "A dust storm has engulfed {name}, airborne dust at {dust} µg/m³. Visibility and air quality are plummeting. Stay indoors, seal windows, and mask up if you must go out.",
    "Thick dust is choking the air over {name} at {dust} µg/m³. Keep windows shut, limit time outside, and wear a mask if you have to be out in it.",
]


def _current(lat: float, lon: float) -> dict | None:
    try:
        resp = requests.get(
            FORECAST_URL,
            headers={"User-Agent": USER_AGENT},
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,apparent_temperature,wind_speed_10m,wind_gusts_10m,wind_direction_10m,visibility,weather_code,precipitation",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("current") or {}
    except (requests.RequestException, ValueError):
        return None


def _dust(lat: float, lon: float) -> float | None:
    """Current airborne dust (µg/m³) from the Open-Meteo air-quality feed.
    Separate endpoint from the main forecast; returns None on any failure."""
    try:
        resp = requests.get(
            AIR_QUALITY_URL,
            headers={"User-Agent": USER_AGENT},
            params={"latitude": lat, "longitude": lon, "current": "dust"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return (resp.json().get("current") or {}).get("dust")
    except (requests.RequestException, ValueError):
        return None


def gulf_signals(
    locations: list[dict],
    heat_feels_c: float,
    wind_gust_kmh: float,
    fog_visibility_m: float = 1000,
    rain_mm: float = 7,
    dust_threshold: float = 500,
) -> list[Signal]:
    def _one(loc: dict) -> list[Signal]:
        signals: list[Signal] = []
        name, lat, lon = loc.get("name"), loc.get("lat"), loc.get("lon")
        zone = loc.get("tz", "UTC")
        if name is None or lat is None or lon is None:
            return signals
        cur = _current(lat, lon)
        if not cur:
            return signals
        cc = tz.code_for_zone(zone) or ""
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
                    topic="heat",
                    country=cc,
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
                    topic="wind",
                    country=cc,
                )
            )

        # Dense fog — a major Gulf road-safety hazard (visibility in metres).
        vis = cur.get("visibility")
        if vis is not None and vis < fog_visibility_m:
            key = f"gulffog:{name}:{today}"
            signals.append(
                Signal(
                    category="gulf",
                    severity=60,
                    text=pick(FOG_VARIANTS, key).format(name=name, vis=round(vis / 10) * 10),
                    dedup_key=key,
                    hashtags=["#Fog", "#Gulf"],
                    tz=zone,
                    tier="advisory",
                    topic="fog",
                    country=cc,
                )
            )

        # Thunderstorms (WMO weather codes 95/96/99).
        code = cur.get("weather_code")
        if code is not None and int(code) in THUNDER_CODES:
            key = f"gulfstorm:{name}:{today}"
            signals.append(
                Signal(
                    category="gulf",
                    severity=75,
                    text=pick(THUNDER_VARIANTS, key).format(name=name),
                    dedup_key=key,
                    hashtags=["#Storm", "#Gulf"],
                    tz=zone,
                    topic="thunderstorm",
                    country=cc,
                )
            )

        # Heavy rain / flash flooding (mm in the current hour).
        rain = cur.get("precipitation")
        if rain is not None and rain >= rain_mm:
            key = f"gulfrain:{name}:{today}"
            signals.append(
                Signal(
                    category="gulf",
                    severity=78,
                    text=pick(RAIN_VARIANTS, key).format(name=name, rain=round(rain)),
                    dedup_key=key,
                    hashtags=["#Flood", "#Gulf"],
                    tz=zone,
                    topic="flood",
                    country=cc,
                )
            )

        # Dust storm (airborne dust from the air-quality feed, µg/m³).
        dust = _dust(lat, lon)
        if dust is not None and dust >= dust_threshold:
            key = f"gulfdust:{name}:{today}"
            signals.append(
                Signal(
                    category="gulf",
                    severity=72,
                    text=pick(DUST_VARIANTS, key).format(name=name, dust=round(dust)),
                    dedup_key=key,
                    hashtags=["#DustStorm", "#Gulf"],
                    tz=zone,
                    topic="dust",
                    country=cc,
                )
            )
        return signals

    return gather(_one, locations)
