"""USGS earthquakes — global, keyless GeoJSON feed of significant quakes.

More responsive than GDACS (which only fires on Orange/Red), so it catches
major quakes worldwide as they're reported. Each is stamped in the local time
of the epicentre.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from ..config import USER_AGENT
from .. import tz
from . import Signal

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

        place = p.get("place") or "an offshore region"
        if p.get("tsunami") == 1:
            note = "Coastal areas near the epicentre should follow any tsunami warnings issued by local authorities."
        else:
            note = "Aftershocks are possible, so stay clear of damaged structures and be ready for further shaking."
        text = f"A magnitude {mag:.1f} earthquake has struck {place}. {note}"

        coords = (feat.get("geometry") or {}).get("coordinates") or []
        zone = tz.zone_for_coords(coords[0], coords[1]) if len(coords) >= 2 else None

        signals.append(
            Signal(
                category="earthquake",
                severity=min(95, int(40 + mag * 8)),
                text=text,
                dedup_key=f"quake:{feat.get('id')}",
                hashtags=["#Earthquake", "#Seismic"],
                tz=zone,
            )
        )
    return signals


def active_count(min_magnitude: float = 6.0, max_age_hours: int = 6) -> int:
    return len(quake_signals(min_magnitude, max_age_hours))
