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
from .. import region as geo
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
    # Sea ice / icebergs. Avoid the bare word "ICE" (matches NOTICE, SERVICE...).
    ("ice", ["ICEBERG", "GROWLER", "PACK ICE", "SEA ICE", "DRIFT ICE",
             "ICE FIELD", "GLACIAL ICE", "BERGY", "ICE LIMIT", "ICE EDGE"]),
    # Drifting hazards and subsea cable/pipeline work.
    ("cable", ["SUBMARINE CABLE", "CABLE OPERATION", "CABLE LAYING", "PIPELINE",
               "DERELICT", "ADRIFT", "DRIFTING OBJECT", "DRIFTING VESSEL",
               "ABANDONED VESSEL", "CONTAINER ADRIFT", "SUBMERGED OBJECT",
               "HAZARD TO NAVIGATION", "OBSTRUCTION"]),
    # Generic disruption at a strategic chokepoint (kept last so specific
    # hazards above win; this only catches otherwise-unclassified warnings).
    ("chokepoint", ["STRAIT OF HORMUZ", "BAB-EL-MANDEB", "BAB EL MANDEB",
                    "STRAIT OF GIBRALTAR", "SUEZ CANAL", "STRAIT OF DOVER",
                    "DARDANELLES", "BOSPORUS", "BOSPHORUS", "KERCH STRAIT"]),
]

# Per-bucket: ranking weight, hashtags, and phrasing variants ({region} filled in).
META = {
    "launch": (84, ["#LaunchHazard", "#Marine"], [
        "A missile or rocket launch hazard area is active in {region}, so vessels should keep well clear until the operation is complete.",
        "Launch operations have closed off part of {region}, so steer clear of the hazard area until it reopens.",
    ]),
    "mine": (84, ["#MineDanger", "#Marine"], [
        "Drifting mines or unexploded ordnance have been reported in {region}, so post a lookout, reduce speed, and keep a safe distance from the area.",
        "A mine danger exists in {region}, so vessels should avoid the area and report any sighting to the authorities.",
    ]),
    "gunfire": (80, ["#LiveFire", "#Marine"], [
        "Naval gunnery or live-fire operations are underway in {region}, so vessels should stand clear of the firing range until it is lifted.",
        "Live-fire exercises are taking place in {region}, so keep well clear of the affected area until the operation ends.",
    ]),
    "exercise": (72, ["#NavalExercise", "#Marine"], [
        "A naval or military exercise is closing off waters in {region}, so route around the area until it reopens.",
        "Military operations are restricting navigation in {region}, so give the area a wide berth until the exercise is complete.",
    ]),
    "gps": (78, ["#GPSInterference", "#Navigation"], [
        "GPS is being jammed across {region}, positions spoofed or knocked out cold. Trust nothing the receiver hands you. Fix your position by radar, visual bearings, and dead reckoning.",
        "Navigators report GPS interference in {region}, the kind that drags your fix off or freezes it dead. Cross-check every position against radar and landmarks, and do not steer on GPS alone.",
    ]),
    "ice": (80, ["#SeaIce", "#Marine"], [
        "Ice is drifting into the shipping lanes across {region}. Icebergs and growlers ride low and hard to spot. Post a lookout, cut your speed, and give any ice a wide margin.",
        "An ice hazard is in force in {region}, bergs and growlers adrift in the sea lanes. Slow down, keep radar and a lookout on watch, and steer well clear.",
    ]),
    "cable": (74, ["#NavWarning", "#Marine"], [
        "A drifting hazard is in force in {region}, adrift objects or subsea cable and pipeline work in the area. Post a lookout, give it room, and report any sighting.",
        "Mariners are warned of an obstruction in {region}, from derelict vessels and debris to cable and pipeline operations. Keep clear, slow down, and steer around the marked area.",
    ]),
    "chokepoint": (76, ["#NavWarning", "#Marine"], [
        "A navigation hazard is in force in {region}, one of the world's busiest chokepoints. Traffic is dense and the margins are thin. Slow down, keep a sharp watch, and follow the routing in force.",
        "Mariners are warned of disruption in {region}, a strategic strait where shipping funnels tight. Expect congestion and stay alert to traffic and instructions until it clears.",
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
    # Keep the region name from dominating the post; fall back to the first
    # part (or the nav-area name) if the joined header runs long.
    if len(region) > 50:
        region = geo[0]
        if len(region) > 50:
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
        if not geo.text_in_scope(text):
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
                tier="critical" if cat in ("launch", "mine", "gunfire") else "serious",
            )
        )
    return signals
