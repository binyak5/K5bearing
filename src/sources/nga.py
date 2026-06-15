"""Global maritime security / military navigation warnings, from the NGA
Maritime Safety Information broadcast-warning service.

One worldwide feed (NAVAREA IV/XII plus HYDROLANT/HYDROPAC/HYDROARC) carries
launch hazard areas, naval gunfire/live-fire zones, mine danger areas, military
exercises closing off shipping lanes, and GPS interference reports. We classify
each in-force warning into one of those buckets and post a clean summary.

Public, keyless. Docs: https://msi.nga.mil
"""
from __future__ import annotations

import requests

from ..config import USER_AGENT
from . import Signal, pick

WARN_URL = "https://msi.nga.mil/api/publications/broadcast-warn?status=active&output=json"
TIMEOUT = 30

# Ordered classification — first matching bucket wins (most specific first).
CATEGORIES = [
    ("launch", ["ROCKET LAUNCH", "SPACE LAUNCH", "MISSILE", "ROCKET FIRING", "LAUNCH"]),
    ("mine", ["MINE DANGER", "DRIFTING MINE", "MINES ADRIFT", "MINES", "MINEFIELD",
              "UNEXPLODED", "ORDNANCE"]),
    ("gps", ["GPS INTERFERENCE", "GPS JAMMING", "GNSS", "JAMMING", "SPOOFING",
             "GPS DEGRAD", "INTERFERENCE"]),
    ("gunfire", ["GUNNERY", "GUNFIRE", "LIVE FIRE", "LIVE-FIRE", "TORPEDO",
                 "FIRING EXERCISE", "FIRING PRACTICE", "NAVAL FIRING", "FIRING"]),
    ("exercise", ["NAVAL EXERCISE", "MILITARY EXERCISE", "MILITARY OPERATION",
                  "NAVAL OPERATION", "HAZARDOUS OPERATIONS", "SUBMARINE",
                  "WARSHIP", "MILITARY ACTIVITY", "EXERCISE"]),
]

# Per-bucket: ranking weight, hashtags, and phrasing variants ({region} filled in).
META = {
    "launch": (84, ["#LaunchHazard", "#Marine"], [
        "A missile or rocket launch hazard area is active in {region}, so vessels should keep well clear until the operation is complete.",
        "Launch operations have closed off part of {region}, so steer clear of the hazard area until it reopens.",
    ]),
    "mine": (84, ["#MineDanger", "#Marine"], [
        "Drifting mines or unexploded ordnance have been reported in {region}, so navigate with extreme caution and keep clear of the area.",
        "A mine danger exists in {region}, so vessels should avoid the area and report any sighting to the authorities.",
    ]),
    "gunfire": (80, ["#LiveFire", "#Marine"], [
        "Naval gunnery or live-fire operations are underway in {region}, so vessels should avoid the firing area until it is lifted.",
        "Live-fire exercises are taking place in {region}, so keep well clear of the danger zone until the operation ends.",
    ]),
    "exercise": (72, ["#NavalExercise", "#Marine"], [
        "A naval or military exercise is closing off waters in {region}, so route around the area until it reopens.",
        "Military operations are restricting navigation in {region}, so give the area a wide berth until the exercise is complete.",
    ]),
    "gps": (78, ["#GPSInterference", "#Navigation"], [
        "GPS interference has been reported in {region}, so verify your position by radar, visual bearings, or dead reckoning.",
        "Navigators report GPS jamming or spoofing in {region}, so cross-check your position and do not rely on GPS alone.",
    ]),
}

# Fallback region name by NGA nav area when the text has no geographic header.
NAVAREA_NAME = {
    "4": "the Western North Atlantic",
    "12": "the Eastern Pacific",
    "A": "the Atlantic",
    "P": "the Pacific and Indian Ocean",
    "C": "the Arctic",
}

_WATER_WORDS = ("SEA", "OCEAN", "GULF", "BAY", "STRAIT", "CHANNEL", "PACIFIC",
                "ATLANTIC", "CARIBBEAN", "MEDITERRANEAN")
_SMALL = {"of", "the", "and"}


def _titlecase(s: str) -> str:
    return " ".join(w.lower() if w.lower() in _SMALL else w.capitalize() for w in s.split())


def _region(text: str, nav_area: str) -> str:
    """Pull the leading geographic header lines into a tidy place name."""
    geo: list[str] = []
    for line in text.splitlines():
        s = line.strip().rstrip(".")
        if not s:
            continue
        if s[0].isdigit() or s.startswith("DNC") or "CHART" in s.upper() or len(s) > 45:
            break
        geo.append(_titlecase(s))
        if len(geo) >= 2:
            break
    region = ", ".join(dict.fromkeys(geo))
    if not region:
        return NAVAREA_NAME.get(nav_area, "international waters")
    first = geo[0].upper()
    if any(w in first for w in _WATER_WORDS) and not first.startswith("THE"):
        region = "the " + region
    return region


def _classify(text: str) -> str | None:
    upper = text.upper()
    for cat, keywords in CATEGORIES:
        if any(k in upper for k in keywords):
            return cat
    return None


def warning_signals(categories: list[str]) -> list[Signal]:
    wanted = set(categories)
    try:
        resp = requests.get(WARN_URL, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return []

    signals: list[Signal] = []
    for w in data.get("broadcast-warn", []):
        text = w.get("text") or ""
        cat = _classify(text)
        if cat is None or cat not in wanted:
            continue
        region = _region(text, str(w.get("navArea", "")))
        severity, hashtags, variants = META[cat]
        key = f"nga:{w.get('navArea')}:{w.get('msgYear')}:{w.get('msgNumber')}"
        signals.append(
            Signal(
                category="maritime",
                severity=severity,
                text=pick(variants, key).format(region=region),
                dedup_key=key,
                hashtags=hashtags,
                tz=None,  # ocean areas span many zones -> UTC
            )
        )
    return signals
