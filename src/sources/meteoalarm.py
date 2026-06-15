"""MeteoAlarm — official EUMETNET severe-weather warnings for ~38 European
countries. Public Atom/CAP feeds, no API key.

Feeds: https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-<country>
Severity is standardized: Moderate (yellow), Severe (orange), Extreme (red).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

from ..config import USER_AGENT
from .. import tz
from . import Signal

FEED_BASE = "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-"
TIMEOUT = 25

NS = {
    "a": "http://www.w3.org/2005/Atom",
    "cap": "urn:oasis:names:tc:emergency:cap:1.2",
}

# Ordering + ranking weight. Higher = more severe.
SEVERITY_RANK = {"Moderate": 1, "Severe": 2, "Extreme": 3}
SEVERITY_WEIGHT = {"Moderate": 55, "Severe": 78, "Extreme": 92}
# MeteoAlarm severity -> public-facing colour word (yellow/orange/red).
SEVERITY_COLOR = {"Moderate": "Yellow", "Severe": "Orange", "Extreme": "Red"}

# Keyword in the event text -> flowing advisory sentence.
HAZARD_ACTIONS = [
    ("thunder", "Severe storms are likely, so stay indoors and away from windows until they pass."),
    ("wind", "Strong winds are expected, so secure anything loose outside and keep away from exposed areas."),
    ("rain", "Heavy rain may bring flooding, so avoid low lying roads and allow extra time to travel."),
    ("flood", "Flooding is possible, so avoid low lying roads and do not drive through water of unknown depth."),
    ("snow", "Snow and ice will make travel difficult, so only head out if your journey is necessary."),
    ("ice", "Ice will make roads and paths treacherous, so take extra care and travel only if you need to."),
    ("fog", "Visibility will be poor, so slow down and keep your lights on while driving."),
    ("forest", "Fire risk is high, so avoid open flames and report any sign of fire immediately."),
    ("fire", "Fire risk is high, so avoid open flames and report any sign of fire immediately."),
    ("heat", "Temperatures will be dangerously high, so stay hydrated and out of the midday sun."),
    ("temperature", "Temperatures will reach an extreme, so limit your exposure and check on those at risk."),
    ("cold", "Temperatures will be dangerously low, so limit time outdoors and dress in warm layers."),
    ("coast", "Coastal conditions will be dangerous, so stay well back from the shoreline and exposed paths."),
    ("avalanche", "Avalanche risk is elevated, so stay off backcountry slopes and follow local guidance."),
]


def _action_for(event: str) -> str:
    low = event.lower()
    for kw, action in HAZARD_ACTIONS:
        if kw in low:
            return action
    return "Stay alert and follow local guidance."


def _hazard(event: str) -> str:
    """Strip leading colour/severity words and trailing 'warning' to a clean noun."""
    words = event.split()
    drop = {"yellow", "orange", "red", "moderate", "severe", "extreme"}
    words = [w for w in words if w.lower() not in drop]
    if words and words[-1].lower() == "warning":
        words = words[:-1]
    return " ".join(words).lower() or "weather"


def _text(entry: ET.Element, tag: str) -> str:
    el = entry.find(f"cap:{tag}", NS)
    if el is None or el.text is None:
        el = entry.find(f"a:{tag}", NS)
    return (el.text or "").strip() if el is not None and el.text else ""


def _country_signals(country: str, min_rank: int) -> list[Signal]:
    url = FEED_BASE + country
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except (requests.RequestException, ET.ParseError):
        return []

    # Collapse the many per-region entries into one signal per (event, severity).
    groups: dict[tuple[str, str], set[str]] = {}
    for entry in root.findall("a:entry", NS):
        severity = _text(entry, "severity")
        if SEVERITY_RANK.get(severity, 0) < min_rank:
            continue
        event = _text(entry, "event") or "Weather warning"
        area = _text(entry, "areaDesc")
        groups.setdefault((event, severity), set()).add(area)

    label = country.replace("-", " ").title()
    tag = "#" + label.replace(" ", "")
    zone = tz.zone_for_country(country)
    signals: list[Signal] = []
    for (event, severity), areas in groups.items():
        color = SEVERITY_COLOR.get(severity, severity).lower()
        article = "An" if color[:1] in "aeiou" else "A"
        hazard = _hazard(event)
        n = len([a for a in areas if a])
        where = f", covering {n} regions" if n > 1 else ""
        text = (
            f"{article} {color} {hazard} warning is in effect for "
            f"{label}{where}. {_action_for(event)}"
        )
        signals.append(
            Signal(
                category="weather_eu",
                severity=SEVERITY_WEIGHT.get(severity, 60),
                text=text,
                dedup_key=f"eu:{country}:{event}:{severity}",
                hashtags=["#WeatherAlert", tag],
                tz=zone,
            )
        )
    return signals


def weather_signals(countries: list[str], min_severity: str = "Severe") -> list[Signal]:
    min_rank = SEVERITY_RANK.get(min_severity, 2)
    signals: list[Signal] = []
    for country in countries:
        signals.extend(_country_signals(country, min_rank))
    return signals


def active_count(countries: list[str], min_severity: str = "Severe") -> int:
    return len(weather_signals(countries, min_severity))
