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
from . import Signal, pick
from . import nws  # reuse the US action wording for Europe

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

# How the warning is announced; one is picked per alert for variety.
OPENERS = [
    "{article} {color} {hazard} warning is in effect for {label}{where}.",
    "{article} {color} {hazard} warning has been issued for {label}{where}.",
    "{article} {color} {hazard} warning is now active for {label}{where}.",
]

# MeteoAlarm hazard keyword -> the US NWS event whose (better, single-source)
# action wording we reuse. Matched in order; the keyword is also the stable
# dedup token, so per-region wording variations collapse into one post.
# Hazards with no clean US equivalent (rain, fog, temperature) keep EU lines.
HAZARD_MAP = [
    ("thunder", ("nws", "Severe Thunderstorm Warning")),
    ("wind", ("nws", "High Wind Warning")),
    ("avalanche", ("nws", "Avalanche Warning")),
    ("snow", ("nws", "Winter Storm Warning")),
    ("ice", ("nws", "Ice Storm Warning")),
    ("flood", ("nws", "Flood Warning")),
    ("forest", ("nws", "Red Flag Warning")),
    ("fire", ("nws", "Red Flag Warning")),
    ("coast", ("nws", "Coastal Flood Warning")),
    ("high-temp", ("nws", "Extreme Heat Warning")),
    ("heat", ("nws", "Extreme Heat Warning")),
    ("low-temp", ("nws", "Extreme Cold Warning")),
    ("cold", ("nws", "Extreme Cold Warning")),
    ("rain", ("eu", [
        "Heavy rain may bring flooding. Avoid low lying roads and allow extra time to travel.",
        "Persistent heavy rain could cause flooding. Steer clear of low ground and plan for delays.",
    ])),
    ("fog", ("eu", [
        "Visibility will be poor. Slow down and keep your lights on while driving.",
        "Dense fog is expected. Reduce speed and use dipped headlights on the road.",
    ])),
    ("temperature", ("eu", [
        "Temperatures will reach an extreme. Limit your exposure and check on those at risk.",
        "An extreme in temperature is expected. Take it easy and look in on the vulnerable.",
    ])),
]

DEFAULT_ACTIONS = [
    "Conditions could get rough. Stay alert and follow local guidance.",
    "The situation may turn unsafe. Stay aware and follow local advice.",
]


def _classify(event: str) -> tuple[str, list[str]]:
    """Return (stable dedup token, action variants) for a MeteoAlarm event."""
    low = event.lower()
    for kw, (kind, target) in HAZARD_MAP:
        if kw in low:
            return kw, (nws.ACTIONS[target] if kind == "nws" else target)
    return "other", DEFAULT_ACTIONS


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

    # Collapse all per-region entries of the same hazard into ONE signal per
    # (hazard token, severity). Keying on the normalized token (not the raw
    # event string, which varies by region) prevents the same event posting
    # twice with different wording.
    groups: dict[tuple[str, str], dict] = {}
    for entry in root.findall("a:entry", NS):
        severity = _text(entry, "severity")
        if SEVERITY_RANK.get(severity, 0) < min_rank:
            continue
        event = _text(entry, "event") or "Weather warning"
        token, actions = _classify(event)
        g = groups.setdefault((token, severity), {"event": event, "actions": actions, "areas": set()})
        g["areas"].add(_text(entry, "areaDesc"))

    label = country.replace("-", " ").title()
    tag = "#" + label.replace(" ", "")
    zone = tz.zone_for_country(country)
    signals: list[Signal] = []
    for (token, severity), g in groups.items():
        color = SEVERITY_COLOR.get(severity, severity).lower()
        article = "An" if color[:1] in "aeiou" else "A"
        hazard = _hazard(g["event"])
        n = len([a for a in g["areas"] if a])
        where = f", covering {n} regions" if n > 1 else ""
        key = f"eu:{country}:{token}:{severity}"
        opener = pick(OPENERS, key + ":o").format(
            article=article, color=color, hazard=hazard, label=label, where=where
        )
        text = f"{opener} {pick(g['actions'], key + ':a')}"
        signals.append(
            Signal(
                category="weather_eu",
                severity=SEVERITY_WEIGHT.get(severity, 60),
                text=text,
                dedup_key=key,
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
