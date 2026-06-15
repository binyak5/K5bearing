"""NOAA Space Weather Prediction Center (SWPC) — solar storms, geomagnetic
activity, and the compass-accuracy signal derived from the Kp index.

All endpoints are public, free, and require no API key.
"""
from __future__ import annotations

import requests

from ..config import USER_AGENT
from . import Signal

KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
ALERTS_URL = "https://services.swpc.noaa.gov/products/alerts.json"

TIMEOUT = 20

# Kp -> NOAA G-scale geomagnetic storm level.
G_SCALE = {5: "G1", 6: "G2", 7: "G3", 8: "G4", 9: "G5"}


def _get_json(url: str):
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def current_kp() -> float | None:
    """Most recent planetary K-index value (0-9).

    Feed is a list of dicts: {"time_tag", "Kp", "a_running", "station_count"}.
    """
    try:
        rows = _get_json(KP_URL)
    except (requests.RequestException, ValueError):
        return None
    if not rows:
        return None
    try:
        return float(rows[-1]["Kp"])
    except (ValueError, KeyError, TypeError, IndexError):
        return None


def compass_status(kp: float | None) -> tuple[str, str]:
    """Map Kp to a (label, advisory) for compass / magnetic navigation.

    Geomagnetic storms transiently shift magnetic declination, which is what
    degrades magnetic-compass accuracy — most severely at high latitudes.
    """
    if kp is None:
        return "Unknown", "Compass reliability data unavailable."
    if kp < 4:
        return "Nominal", "Magnetic compass reliable. Standard declination applies."
    if kp < 5:
        return "Unsettled", "Minor declination drift possible at high latitudes."
    if kp < 7:
        return "Degraded", "Compass declination may swing several degrees. Cross-check bearings with GPS/landmarks."
    return "Unreliable", "Significant magnetic disturbance. Do not trust compass alone — verify with GPS/celestial."


def geomagnetic_signal(kp_threshold: int) -> Signal | None:
    kp = current_kp()
    if kp is None or kp < kp_threshold:
        return None
    level = G_SCALE.get(int(kp), "G1")
    label, advisory = compass_status(kp)
    text = (
        f"GEOMAGNETIC STORM — {level} (Kp {kp:.0f})\n"
        f"Compass: {label}. {advisory}"
    )
    # Dedup per storm level per day so escalations re-post but steady state doesn't.
    return Signal(
        category="geomagnetic",
        severity=50 + int(kp) * 5,
        text=text,
        dedup_key=f"geomag:{level}",
        hashtags=["#K5Bearing", "#GeomagneticStorm", "#Compass"],
    )


def _alert_headline(message: str) -> str:
    """Pull the human 'ALERT:'/'WARNING:'/'SUMMARY:' line out of an SWPC message."""
    for line in message.splitlines():
        s = line.strip()
        for tag in ("ALERT:", "WARNING:", "SUMMARY:", "WATCH:"):
            if s.startswith(tag):
                return s[len(tag):].strip()
    return ""


def solar_signals(watch_prefixes: list[str]) -> list[Signal]:
    try:
        rows = _get_json(ALERTS_URL)
    except (requests.RequestException, ValueError):
        return []

    signals: list[Signal] = []
    # Newest first; only consider the most recent handful.
    for entry in rows[:25]:
        pid = (entry.get("product_id") or "").strip()
        if not any(pid.startswith(p) for p in watch_prefixes):
            continue
        message = entry.get("message", "")
        headline = _alert_headline(message)
        if not headline:
            continue
        issued = (entry.get("issue_datetime") or "").strip()
        text = f"SPACE WEATHER — {headline[:200]}"
        signals.append(
            Signal(
                category="solar",
                severity=60,
                text=text,
                dedup_key=f"solar:{pid}:{issued}",
                hashtags=["#K5Bearing", "#SolarStorm", "#SpaceWeather"],
            )
        )
    return signals
