"""USGS earthquakes — global, keyless GeoJSON feed of significant quakes.

More responsive than GDACS (which only fires on Orange/Red), so it catches
major quakes worldwide as they're reported. Each is stamped in the local time
of the epicentre.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from ..config import USER_AGENT
from .. import tz, region
from . import Signal, pick

LEADS = [
    "A magnitude {mag} earthquake has hit {place}.",
]
TSUNAMI_NOTES = [
    "Coastal areas near the epicentre should follow any tsunami warnings issued by local authorities.",
]
AFTERSHOCK_NOTES = [
    "Expect possible aftershocks. Keep away from weakened buildings and be ready for further shaking.",
]

# 4.5+ over the last day; we then filter by magnitude and recency ourselves.
FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
TIMEOUT = 20


def quake_signals(min_magnitude: float = 6.0, max_age_hours: int = 6) -> list[Signal]:
    try:
        resp = requests.get(FEED_URL, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    signals: list[Signal] = []
    for feat in data.get("features", []):
        p = feat.get("properties", {})
        mag = p.get("mag")
        if mag is None or mag < min_magnitude:
            continue
        when_ms = p.get("time")
        if when_ms and datetime.fromtimestamp(when_ms / 1000, timezone.utc) < cutoff:
            continue

        coords = (feat.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2 or not region.in_scope(coords[1], coords[0]):
            continue

        place = p.get("place") or "an offshore region"
        key = f"quake:{feat.get('id')}"
        lead = pick(LEADS, key + ":l").format(mag=f"{mag:.1f}", place=place)
        notes = TSUNAMI_NOTES if p.get("tsunami") == 1 else AFTERSHOCK_NOTES
        text = f"{lead} {pick(notes, key + ':n')}"

        zone = tz.zone_for_coords(coords[0], coords[1])

        signals.append(
            Signal(
                category="earthquake",
                # M5≈75, M6≈86, M7≈97 — keeps great quakes at the top without
                # letting a minor M5 outrank serious severe-weather warnings.
                severity=min(98, int(20 + mag * 11)),
                text=text,
                dedup_key=key,
                hashtags=["#Earthquake", "#Seismic"],
                tz=zone,
                tier="critical" if p.get("tsunami") == 1 or mag >= 7.0 else "serious",
            )
        )
    return signals


def active_count(min_magnitude: float = 6.0, max_age_hours: int = 6) -> int:
    return len(quake_signals(min_magnitude, max_age_hours))
