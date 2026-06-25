"""Outdoor-safety signals from Open-Meteo (keyless): extreme UV index, dust
storms, and violent thunderstorms for a watchlist of locations.

Unlike the event feeds, these are continuous values, so we poll a configured
set of places and only post when one crosses a high threshold.
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

from ..config import USER_AGENT
from .. import tz, region
from . import Signal, pick, gather

# The city now rides in the geo tag ("USA, Miami:"), like the other regional
# sources, so it's no longer repeated in the body.
UV_VARIANTS = [
    "The UV index has reached {uv}, an extreme level. Cover up and seek "
    "shade through the middle of the day.",
    "UV has spiked to {uv}, in the extreme range. Cover exposed skin and "
    "stay shaded around midday.",
]

DUST_VARIANTS = [
    "Thick dust is filling the air, pushing levels to {dust} µg/m³. Limit time "
    "outside, close everything up, and protect your eyes and lungs.",
]

LIGHTNING_VARIANTS = [
    "Violent thunderstorms are rolling through, packing severe lightning"
    "{hail}. Seek solid shelter, stay off open ground and water, and wait it out.",
]


def _geo(name: str, lat: float, lon: float) -> str:
    """The "REGION, city" geo tag (e.g. 'USA, Miami'), or the bare city if the
    location somehow falls outside the covered regions."""
    code = region.code_for(lat, lon)
    return f"{code}, {name}" if code else name

# WMO weather codes for thunderstorms -> hail clause.
THUNDER_CODES = {95: "", 96: " and hail", 99: " and large hail"}

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 20


def _current(lat: float, lon: float) -> dict | None:
    try:
        resp = requests.get(
            AQ_URL,
            headers={"User-Agent": USER_AGENT},
            params={"latitude": lat, "longitude": lon, "current": "uv_index,dust"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("current") or {}
    except (requests.RequestException, ValueError):
        return None


def _weather_code(lat: float, lon: float) -> int | None:
    try:
        resp = requests.get(
            FORECAST_URL,
            headers={"User-Agent": USER_AGENT},
            params={"latitude": lat, "longitude": lon, "current": "weather_code"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("current", {}).get("weather_code")
    except (requests.RequestException, ValueError):
        return None


def lightning_signals(locations: list[dict]) -> list[Signal]:
    """Violent thunderstorms (WMO codes 95/96/99) over the watched locations."""
    today = datetime.now(timezone.utc).date().isoformat()

    def _one(loc: dict) -> Signal | None:
        name = loc.get("name")
        lat, lon = loc.get("lat"), loc.get("lon")
        if name is None or lat is None or lon is None:
            return None
        code = _weather_code(lat, lon)
        if code not in THUNDER_CODES:
            return None
        key = f"storm:{name}:{today}"
        return Signal(
            category="outdoor",
            severity=60,
            text=pick(LIGHTNING_VARIANTS, key).format(hail=THUNDER_CODES[code]),
            dedup_key=key,
            hashtags=["#Lightning", "#SevereWeather"],
            tz=tz.zone_for_coords(lon, lat),
            country=_geo(name, lat, lon),
            card={
                "value": "Lightning",
                "event": "Thunderstorm",
                "detail": name,
                "lat": lat, "lon": lon,
            },
        )

    return gather(_one, locations)


def outdoor_signals(
    locations: list[dict],
    uv_threshold: float,
    dust_threshold: float,
) -> list[Signal]:
    today = datetime.now(timezone.utc).date().isoformat()

    def _one(loc: dict) -> list[Signal]:
        name = loc.get("name")
        lat, lon = loc.get("lat"), loc.get("lon")
        if name is None or lat is None or lon is None:
            return []
        cur = _current(lat, lon)
        if not cur:
            return []
        zone = tz.zone_for_coords(lon, lat)
        out: list[Signal] = []

        uv = cur.get("uv_index")
        if uv is not None and uv >= uv_threshold:
            uv_key = f"uv:{name}:{today}"
            out.append(
                Signal(
                    category="outdoor",
                    severity=50,
                    text=pick(UV_VARIANTS, uv_key).format(uv=f"{uv:.0f}"),
                    dedup_key=uv_key,
                    hashtags=["#UVindex", "#OutdoorSafety"],
                    tz=zone,
                    tier="advisory",
                    country=_geo(name, lat, lon),
                )
            )

        dust = cur.get("dust")
        if dust is not None and dust >= dust_threshold:
            dust_key = f"dust:{name}:{today}"
            out.append(
                Signal(
                    category="outdoor",
                    severity=62,
                    text=pick(DUST_VARIANTS, dust_key).format(dust=int(dust)),
                    dedup_key=dust_key,
                    hashtags=["#DustStorm", "#AirQuality"],
                    tz=zone,
                    country=_geo(name, lat, lon),
                )
            )
        return out

    return gather(_one, locations)
