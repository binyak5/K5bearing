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

WIND_VARIANTS = [
    "{cat} winds are raking {area} at {w} knots and gusting to {g}. Small craft have no business out there, and larger vessels should batten down and rig for heavy weather.",
    "A {cat_low} blow has set in over {area}, winds at {w} knots and gusts to {g}. Hold port if you are small, and lash down everything topside if you are not.",
]

SWELL_VARIANTS = [
    "A long-period swell is marching into {area}, {h} m sets rolling through every {p} seconds. It looks calm offshore, but harbor mouths and surf zones will turn dangerous. Stay off exposed rocks and jetties.",
    "Powerful long-period groundswell is pushing into {area}, {h} m and spaced {p} seconds apart. That energy stacks up fast in the shallows. Expect sneaker sets and treacherous surf around inlets and bars.",
]

SURF_VARIANTS = [
    "Seas are breaking heavily across {area}, {h} m waves stacking up at the entrance. Bar and surf-zone conditions are dangerous. Time any crossing for slack water or stay in.",
    "A rough bar is running at {area}, where {h} m swells pile into the shallows and break hard. Small craft should hold off until it lays down.",
]


def _wind_category(kt: float) -> tuple[str, int]:
    """Return (label, ranking weight) for a sustained/gust wind in knots."""
    if kt >= 64:
        return "Hurricane-force", 90
    if kt >= 48:
        return "Storm-force", 84
    return "Gale-force", 78


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


def _wind(lat: float, lon: float) -> tuple[float | None, float | None]:
    """Sustained wind and gust at 10 m, in knots."""
    try:
        resp = requests.get(
            FORECAST_URL,
            headers={"User-Agent": USER_AGENT},
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "wind_speed_10m,wind_gusts_10m",
                "wind_speed_unit": "kn",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        cur = resp.json().get("current", {})
        return cur.get("wind_speed_10m"), cur.get("wind_gusts_10m")
    except (requests.RequestException, ValueError):
        return None, None


def _swell(lat: float, lon: float) -> tuple[float | None, float | None]:
    """Swell-component wave height (m) and period (s) — the long groundswell,
    distinct from local wind chop."""
    try:
        resp = requests.get(
            MARINE_URL,
            headers={"User-Agent": USER_AGENT},
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "swell_wave_height,swell_wave_period",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        cur = resp.json().get("current", {})
        return cur.get("swell_wave_height"), cur.get("swell_wave_period")
    except (requests.RequestException, ValueError):
        return None, None


def wind_signals(areas: list[dict], gale_kt: float) -> list[Signal]:
    """Gale, storm, or hurricane-force winds over the watched sea areas."""
    today = datetime.now(timezone.utc).date().isoformat()
    signals: list[Signal] = []
    for a in areas:
        name, lat, lon = a.get("name"), a.get("lat"), a.get("lon")
        if name is None or lat is None or lon is None:
            continue
        spd, gust = _wind(lat, lon)
        ref = gust if gust is not None else spd  # gusts are what hit you
        if ref is None or ref < gale_kt:
            continue
        cat, weight = _wind_category(ref)
        key = f"seawind:{name}:{today}"
        signals.append(
            Signal(
                category="marine",
                severity=weight,
                text=pick(WIND_VARIANTS, key).format(
                    cat=cat,
                    cat_low=cat.lower(),
                    area="the " + name,
                    w=round(spd) if spd is not None else round(ref),
                    g=round(gust) if gust is not None else round(ref),
                ),
                dedup_key=key,
                hashtags=["#GaleWarning", "#Marine"],
                tz=None,
            )
        )
    return signals


def swell_signals(areas: list[dict], period_s: float, height_m: float) -> list[Signal]:
    """Dangerous long-period swell over the watched sea areas."""
    today = datetime.now(timezone.utc).date().isoformat()
    signals: list[Signal] = []
    for a in areas:
        name, lat, lon = a.get("name"), a.get("lat"), a.get("lon")
        if name is None or lat is None or lon is None:
            continue
        h, p = _swell(lat, lon)
        if h is None or p is None or p < period_s or h < height_m:
            continue
        key = f"swell:{name}:{today}"
        signals.append(
            Signal(
                category="marine",
                severity=74,
                text=pick(SWELL_VARIANTS, key).format(area="the " + name, h=round(h, 1), p=round(p)),
                dedup_key=key,
                hashtags=["#GroundSwell", "#Marine"],
                tz=None,
            )
        )
    return signals


def surf_signals(zones: list[dict], threshold: float) -> list[Signal]:
    """Rough-bar / surf-zone risk at coastal entrances and inlets."""
    today = datetime.now(timezone.utc).date().isoformat()
    signals: list[Signal] = []
    for z in zones:
        name, lat, lon = z.get("name"), z.get("lat"), z.get("lon")
        if name is None or lat is None or lon is None:
            continue
        h = _wave_height(lat, lon)
        if h is None or h < threshold:
            continue
        key = f"surf:{name}:{today}"
        signals.append(
            Signal(
                category="marine",
                severity=70,
                text=pick(SURF_VARIANTS, key).format(area="the " + name, h=round(h, 1)),
                dedup_key=key,
                hashtags=["#SurfZone", "#Marine"],
                tz=None,
            )
        )
    return signals


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
