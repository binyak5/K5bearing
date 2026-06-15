"""Marine sea-state warnings from Open-Meteo's Marine API (keyless).

European seas have no single keyless marine-warning feed the way US waters do
(NWS), so we poll significant wave height for a watchlist of named sea areas
(European-focused, plus key global ones) and warn when seas run high.

WMO sea-state scale: 4-6 m high, 6-9 m very high, 9 m+ phenomenal.
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

from ..config import USER_AGENT
from . import Signal, pick

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 20

VARIANTS = [
    "{cat} seas running to {h}m are reported in {area}, so small craft should stay in port and larger vessels should rig for heavy weather.",
    "Seas are building to {h}m ({low}) in {area}, so secure for heavy weather and keep well clear of exposed waters.",
]

FOG_VARIANTS = [
    "Dense fog has settled over {area}, dropping visibility to around {v} m. Slow down, sound your fog signals, and post a lookout.",
    "Thick fog is blanketing {area}, with visibility under {v} m. Cut your speed, keep a sharp lookout, and lean on radar and signals.",
]


def _category(h: float) -> tuple[str, int]:
    """Return (label, ranking weight) for a significant wave height in metres."""
    if h >= 9:
        return "Phenomenal", 88
    if h >= 6:
        return "Very high", 82
    return "High", 76


def _wave_height(lat: float, lon: float) -> float | None:
    try:
        resp = requests.get(
            MARINE_URL,
            headers={"User-Agent": USER_AGENT},
            params={"latitude": lat, "longitude": lon, "current": "wave_height"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("current", {}).get("wave_height")
    except (requests.RequestException, ValueError):
        return None


def _visibility(lat: float, lon: float) -> float | None:
    try:
        resp = requests.get(
            FORECAST_URL,
            headers={"User-Agent": USER_AGENT},
            params={"latitude": lat, "longitude": lon, "current": "visibility"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("current", {}).get("visibility")
    except (requests.RequestException, ValueError):
        return None


def fog_signals(areas: list[dict], visibility_m: float) -> list[Signal]:
    """Dense fog at sea (low visibility) for the watched sea areas."""
    today = datetime.now(timezone.utc).date().isoformat()
    signals: list[Signal] = []
    for a in areas:
        name, lat, lon = a.get("name"), a.get("lat"), a.get("lon")
        if name is None or lat is None or lon is None:
            continue
        vis = _visibility(lat, lon)
        if vis is None or vis >= visibility_m:
            continue
        key = f"marinefog:{name}:{today}"
        signals.append(
            Signal(
                category="marine",
                severity=72,
                text=pick(FOG_VARIANTS, key).format(area="the " + name, v=int(round(vis / 50) * 50)),
                dedup_key=key,
                hashtags=["#MarineFog", "#Marine"],
                tz=None,
            )
        )
    return signals


def sea_signals(areas: list[dict], threshold: float) -> list[Signal]:
    today = datetime.now(timezone.utc).date().isoformat()
    signals: list[Signal] = []
    for a in areas:
        name, lat, lon = a.get("name"), a.get("lat"), a.get("lon")
        if name is None or lat is None or lon is None:
            continue
        h = _wave_height(lat, lon)
        if h is None or h < threshold:
            continue
        cat, weight = _category(h)
        area = "the " + name
        key = f"seas:{name}:{today}"
        signals.append(
            Signal(
                category="marine",
                severity=weight,
                text=pick(VARIANTS, key).format(cat=cat, low=cat.lower(), h=round(h), area=area),
                dedup_key=key,
                hashtags=["#HighSeas", "#Marine"],
                tz=None,  # open sea spans many zones -> UTC
            )
        )
    return signals
