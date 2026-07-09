"""Tide post for Hoek van Holland — the mouth of the Nieuwe Waterweg, Rotterdam's
sea gate. Announces the next predicted high water from Rijkswaterstaat's open
WaterWebservices (keyless).

Data: the DDAPI 2.0 OphalenWaarnemingen service, groepering GETETBRKD2
("getijextreem berekend" — calculated tidal extremes), which returns the day's
predicted high/low water heights in cm relative to NAP. The service doesn't
label each extreme high vs low, but tidal extremes strictly alternate, so we
classify them by whether each is a local maximum (high) or minimum (low).

Fires once per high-water event, in the run-up to it, as a timely heads-up. Any
API/parse failure returns nothing — it never guesses or posts a wrong time.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import requests

from ..config import USER_AGENT
from . import Signal, pick

OBS_URL = ("https://ddapi20-waterwebservices.rijkswaterstaat.nl"
           "/ONLINEWAARNEMINGENSERVICES/OphalenWaarnemingen")
TIMEOUT = 30

TIDE_VARIANTS = [
    "Next high water at {name}: {time}, {height} m.",
]


def _parse(ts: str):
    try:
        return datetime.fromisoformat(ts)   # tz-aware (carries the API's offset)
    except (ValueError, TypeError):
        return None


def _fetch_extremes(code: str, hours: int = 30) -> list[tuple[datetime, float]] | None:
    """(utc-aware time, height cm NAP) for each predicted tidal extreme in the
    window, sorted by time. None on any request/parse failure."""
    now = datetime.now(timezone.utc)
    body = {
        "AquoPlusWaarnemingMetadata": {"AquoMetadata": {
            "Compartiment": {"Code": "OW"},
            "Grootheid": {"Code": "WATHTE"},
            "Groepering": {"Code": "GETETBRKD2"},   # calculated tidal extremes
            "Hoedanigheid": {"Code": "NAP"},
        }},
        "Locatie": {"Code": code},
        "Periode": {
            "Begindatumtijd": now.strftime("%Y-%m-%dT%H:%M:%S.000+00:00"),
            "Einddatumtijd": (now + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S.000+00:00"),
        },
    }
    try:
        resp = requests.post(OBS_URL, json=body,
                             headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
                             timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("Succesvol"):
            return None
        series = data.get("WaarnemingenLijst") or []
        if not series:
            return None
        out: list[tuple[datetime, float]] = []
        for m in series[0].get("MetingenLijst") or []:
            t = _parse(m.get("Tijdstip"))
            v = (m.get("Meetwaarde") or {}).get("Waarde_Numeriek")
            if t is not None and isinstance(v, (int, float)) and abs(v) < 1e6:
                out.append((t.astimezone(timezone.utc), float(v)))
        out.sort(key=lambda x: x[0])
        return out or None
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def _high_water_flags(values: list[float]) -> list[bool]:
    """Mark which extremes are high water. Tidal extremes alternate, so fix the
    parity from the first pair (higher of the two is the high) and alternate."""
    n = len(values)
    if n == 1:
        return [True]   # a lone extreme: treat as high (caller still time-filters)
    evens_high = values[0] >= values[1]
    return [((i % 2 == 0) == evens_high) for i in range(n)]


def next_high_water(code: str, zone: str):
    """(local-time datetime, height in metres) of the next predicted high water,
    or None. Times are converted to `zone` (the API's own offset ignores DST)."""
    extremes = _fetch_extremes(code)
    if not extremes:
        return None
    flags = _high_water_flags([v for _, v in extremes])
    now = datetime.now(timezone.utc)
    for (t, v), is_high in zip(extremes, flags):
        if is_high and t >= now:
            return t.astimezone(ZoneInfo(zone)), round(v / 100.0, 1)
    return None


def tide_signals(cfg: dict) -> list[Signal]:
    code = cfg.get("location_code", "hoekvanholland")
    name = cfg.get("name", "Hoek van Holland")
    zone = cfg.get("tz", "Europe/Amsterdam")
    lead_min = cfg.get("lead_min", 90)

    nxt = next_high_water(code, zone)
    if nxt is None:
        return []
    when, height_m = nxt

    # Only in the run-up to the high water, so it reads as a timely heads-up.
    now_local = datetime.now(ZoneInfo(zone))
    lead = (when - now_local).total_seconds()
    if not (0 <= lead <= lead_min * 60):
        return []

    # Dedup on the specific high-water timestamp -> posted once per event.
    key = f"tide:{code}:{when.isoformat()}"
    text = pick(TIDE_VARIANTS, key).format(name=name, time=when.strftime("%H:%M"),
                                           height=f"{height_m:.1f}")
    return [Signal(
        category="tides",
        severity=42,          # low: a rhythm post, never jumps a real alert
        text=text,
        dedup_key=key,
        hashtags=["#Tides", "#Rotterdam"],
        tz=zone,
        tier="serious",
        topic="tide",
    )]
