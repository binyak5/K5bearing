"""Outdoor-safety signals from Open-Meteo (keyless): extreme UV index for a
watchlist of locations.

Unlike the event feeds, UV is a continuous value, so we poll a configured set
of places and only post when it crosses a high threshold.
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

from ..config import USER_AGENT
from .. import tz
from . import Signal, pick

UV_VARIANTS = [
    "The UV index has reached {uv} in {name}, an extreme level. Cover up, wear "
    "sunglasses and sunscreen, and seek shade through the middle of the day.",
    "UV has spiked to {uv} in {name}, in the extreme range. Wear sunscreen and "
    "shades, cover exposed skin, and stay shaded around midday.",
]

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
TIMEOUT = 20


def _current(lat: float, lon: float) -> dict | None:
    try:
        resp = requests.get(
            AQ_URL,
            headers={"User-Agent": USER_AGENT},
            params={"latitude": lat, "longitude": lon, "current": "uv_index"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("current") or {}
    except (requests.RequestException, ValueError):
        return None


def outdoor_signals(locations: list[dict], uv_threshold: float) -> list[Signal]:
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

        uv = cur.get("uv_index")
        if uv is not None and uv >= uv_threshold:
            uv_key = f"uv:{name}:{today}"
            signals.append(
                Signal(
                    category="outdoor",
                    severity=48,
                    text=pick(UV_VARIANTS, uv_key).format(uv=f"{uv:.0f}", name=name),
                    dedup_key=uv_key,
                    hashtags=["#UVindex", "#OutdoorSafety"],
                    tz=tz.zone_for_coords(lon, lat),
                )
            )
    return signals
