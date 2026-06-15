"""MeteoAlarm — official EUMETNET severe-weather warnings for ~38 European
countries. Public Atom/CAP feeds, no API key.

Feeds: https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-<country>
Severity is standardized: Moderate (yellow), Severe (orange), Extreme (red).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

from ..config import USER_AGENT
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
SEVERITY_BADGE = {"Moderate": "🟡", "Severe": "🟧", "Extreme": "🟥"}


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
    signals: list[Signal] = []
    for (event, severity), areas in groups.items():
        badge = SEVERITY_BADGE.get(severity, "⚠️")
        n = len([a for a in areas if a])
        where = f" — {n} area(s)" if n else ""
        text = f"{badge} {severity.upper()} — {label}\n{event}{where}"
        signals.append(
            Signal(
                category="weather_eu",
                severity=SEVERITY_WEIGHT.get(severity, 60),
                text=text,
                dedup_key=f"eu:{country}:{event}:{severity}",
                hashtags=["#K5Bearing", "#MeteoAlarm", "#WeatherAlert"],
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
