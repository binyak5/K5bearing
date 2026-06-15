"""Outdoor-safety signals from Open-Meteo (keyless): extreme UV index and
unhealthy air quality, for a watchlist of locations.

Unlike the event feeds, UV and air quality are continuous values, so we poll a
configured set of places and only post when they cross a high threshold.
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

from ..config import USER_AGENT
from .. import tz
from . import Signal

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEOUT = 20


def _aqi_category(aqi: int) -> str:
    if aqi >= 301:
        return "hazardous"
    if aqi >= 201:
        return "very unhealthy"
    if aqi >= 151:
        return "unhealthy"
    return "elevated"


def _current(lat: float, lon: float) -> dict | None:
    try:
        resp = requests.get(
            AQ_URL,
            headers={"User-Agent": USER_AGENT},
            params={"latitude": lat, "longitude": lon, "current": "us_aqi,uv_index"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("current") or {}
    except (requests.RequestException, ValueError):
        return None


def outdoor_signals(locations: list[dict], uv_threshold: float, aqi_threshold: int) -> list[Signal]:
    today = datetime.now(timezone.utc).date().isoformat()
    signals: list[Signal] = []
    for loc in locations:
        name = loc.get("name")
        lat, lon = loc.get("lat"), loc.get("lon")
        if name is None or lat is None or lon is None:
            continue
        cur = _current(lat, lon)
        if not cur:
            continue
        zone = tz.zone_for_coords(lon, lat)

        uv = cur.get("uv_index")
        if uv is not None and uv >= uv_threshold:
            signals.append(
                Signal(
                    category="outdoor",
                    severity=48,
                    text=(
                        f"The UV index has reached {uv:.0f} in {name}, an extreme level. "
                        "Cover up, wear sunglasses and sunscreen, and seek shade through "
                        "the middle of the day."
                    ),
                    dedup_key=f"uv:{name}:{today}",
                    hashtags=["#UVindex", "#OutdoorSafety"],
                    tz=zone,
                )
            )

        aqi = cur.get("us_aqi")
        if aqi is not None and aqi >= aqi_threshold:
            signals.append(
                Signal(
                    category="outdoor",
                    severity=52,
                    text=(
                        f"Air quality in {name} has reached {int(aqi)} on the US AQI, "
                        f"in the {_aqi_category(int(aqi))} range. Limit time outdoors, "
                        "keep windows closed, and wear a mask if you must go out."
                    ),
                    dedup_key=f"aqi:{name}:{today}",
                    hashtags=["#AirQuality", "#OutdoorSafety"],
                    tz=zone,
                )
            )
    return signals
