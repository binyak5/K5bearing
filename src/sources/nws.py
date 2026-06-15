"""US National Weather Service — severe-weather, hurricane, and tornado alerts.

Public GeoJSON API, no key required. Docs: https://www.weather.gov/documentation/services-web-api
"""
from __future__ import annotations

import requests

from ..config import USER_AGENT
from . import Signal

ALERTS_URL = "https://api.weather.gov/alerts/active"
TIMEOUT = 20

# NWS severity -> rough ranking weight.
SEVERITY_WEIGHT = {"Extreme": 90, "Severe": 75, "Moderate": 55, "Minor": 40}


def weather_signals(events: list[str], area: str = "") -> list[Signal]:
    params = {"status": "actual", "message_type": "alert"}
    if area:
        params["area"] = area
    try:
        resp = requests.get(
            ALERTS_URL,
            headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
            params=params,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return []

    wanted = set(events)
    signals: list[Signal] = []
    seen_keys: set[str] = set()

    for feat in data.get("features", []):
        props = feat.get("properties", {})
        event = props.get("event", "")
        if event not in wanted:
            continue

        area_desc = props.get("areaDesc", "")
        # Collapse many simultaneous warnings of the same type+area into one post.
        key = f"weather:{event}:{area_desc[:60]}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        headline = props.get("headline") or f"{event} for {area_desc}"
        severity = SEVERITY_WEIGHT.get(props.get("severity", ""), 50)
        text = f"⚠️ {event.upper()}\n{headline[:220]}"

        signals.append(
            Signal(
                category="weather",
                severity=severity,
                text=text,
                dedup_key=key,
                hashtags=["#K5Bearing", "#WeatherAlert"],
            )
        )
    return signals
