"""MeteoAlarm — official EUMETNET severe-weather warnings for ~38 European
countries. Public Atom/CAP feeds, no API key.

Feeds: https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-<country>
Severity is standardized: Moderate (yellow), Severe (orange), Extreme (red).
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests

from ..config import USER_AGENT
from .. import tz
from . import Signal, pick, gather, region_list, geocode, forecast_temp
from . import nws  # reuse the US action wording for Europe

FEED_BASE = "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-"
TIMEOUT = 25

NS = {
    "a": "http://www.w3.org/2005/Atom",
    "cap": "urn:oasis:names:tc:emergency:cap:1.2",
}

# Ordering + ranking weight. Higher = more severe.
SEVERITY_RANK = {"Moderate": 1, "Severe": 2, "Extreme": 3}
SEVERITY_WEIGHT = {"Moderate": 55, "Severe": 79, "Extreme": 96}
# MeteoAlarm severity -> public-facing colour word (yellow/orange/red).
SEVERITY_COLOR = {"Moderate": "Yellow", "Severe": "Orange", "Extreme": "Red"}

# How the warning is announced; one is picked per alert for variety.
OPENERS = [
    "{article} {color} {hazard} warning is active{where}.",
    "{article} {color} {hazard} warning has been issued{where}.",
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
        "Persistent heavy rain could cause flooding. Steer clear of low ground and plan for delays.",
    ])),
    ("fog", ("eu", [
        "Dense fog is expected. Visibility will be poor. Reduce speed and use headlights on the road.",
    ])),
    ("temperature", ("eu", [
        "Temperatures will reach an extreme. Take it easy and look in on the vulnerable.",
    ])),
]

DEFAULT_ACTIONS = [
    "Conditions could get rough. Stay alert and follow local guidance.",
]


def _classify(event: str) -> tuple[str, list[str]]:
    """Return (stable dedup token, action variants) for a MeteoAlarm event."""
    low = event.lower()
    for kw, (kind, target) in HAZARD_MAP:
        if kw in low:
            return kw, (nws.ACTIONS[target] if kind == "nws" else target)
    return "other", DEFAULT_ACTIONS


def _hazard(event: str) -> str:
    """Reduce a MeteoAlarm event to a clean hazard noun, so openers read
    consistently as '{colour} {hazard} warning' (e.g. 'orange heatwave warning').
    Handles both 'Heatwave warning' and Belgium-style 'warning for heatwave'.
    """
    words = event.split()
    drop = {"yellow", "amber", "orange", "red", "moderate", "severe", "extreme"}
    words = [w for w in words if w.lower() not in drop]
    if words and words[-1].lower() == "warning":
        words = words[:-1]
    # Strip a leading "warning for"/"warning of" phrasing -> just the hazard.
    if len(words) >= 2 and words[0].lower() == "warning" and words[1].lower() in ("for", "of"):
        words = words[2:]
    return " ".join(words).lower() or "weather"


def _text(entry: ET.Element, tag: str) -> str:
    el = entry.find(f"cap:{tag}", NS)
    if el is None or el.text is None:
        el = entry.find(f"a:{tag}", NS)
    return (el.text or "").strip() if el is not None and el.text else ""


# MeteoAlarm hazard token -> coarse topic (shared vocab with the US _topic).
_EU_TOPIC = {
    "thunder": "thunderstorm", "wind": "wind", "avalanche": "avalanche",
    "snow": "winter", "ice": "winter", "flood": "flood", "forest": "fire",
    "fire": "fire", "coast": "flood", "rain": "flood", "fog": "fog",
    "high-temp": "heat", "heat": "heat", "low-temp": "cold", "cold": "cold",
    "temperature": "temperature",
}


def _eu_topic(token: str) -> str:
    return _EU_TOPIC.get(token, "weather")


def _parse_dt(s: str):
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


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
    now = datetime.now(timezone.utc)
    today = now.date()
    groups: dict[tuple[str, str], dict] = {}
    for entry in root.findall("a:entry", NS):
        severity = _text(entry, "severity")
        if SEVERITY_RANK.get(severity, 0) < min_rank:
            continue
        # Freshness: only warnings in effect today. Drop expired ones and ones
        # that don't start until a future day.
        onset = _parse_dt(_text(entry, "onset") or _text(entry, "effective"))
        expires = _parse_dt(_text(entry, "expires"))
        if expires is not None and expires < now:
            continue
        if onset is not None and onset.date() > today:
            continue
        # Awareness types arrive as codes like "extreme_heat"; spell them out so
        # they read as words ("extreme heat") in both classification and display.
        event = (_text(entry, "event") or "Weather warning").replace("_", " ")
        token, actions = _classify(event)
        g = groups.setdefault((token, severity), {"event": event, "actions": actions, "areas": set()})
        # Some feeds (e.g. the UK) pack every region into one areaDesc field joined
        # by "|"; others send one entry per region. Split so the regions are always
        # individual items and render with the same comma list everywhere.
        for part in re.split(r"[|;]", _text(entry, "areaDesc")):
            part = part.strip()
            if part:
                g["areas"].add(part)

    country_title = country.replace("-", " ").title()
    tag = "#" + country_title.replace(" ", "")
    zone = tz.zone_for_country(country)
    signals: list[Signal] = []
    for (token, severity), g in groups.items():
        color = SEVERITY_COLOR.get(severity, severity).lower()
        article = "An" if color[:1] in "aeiou" else "A"
        hazard = _hazard(g["event"])
        # Name the actual sub-regions affected. The country now rides in the
        # timestamp prefix ("EU, France"), so we never restate it here: with no
        # named sub-regions we just say the warning is active, no "for {country}".
        region_label = region_list(sorted(g["areas"]))
        where = f" for {region_label}" if region_label else ""
        key = f"eu:{country}:{token}:{severity}"
        opener = pick(OPENERS, key + ":o").format(
            article=article, color=color, hazard=hazard, where=where
        )
        # Heat/cold warnings carry only a colour level (no temperature, no coords),
        # so state an approximate degree: geocode the first named region and take
        # the day's forecast extreme there. One figure for a multi-region warning,
        # so it may under/overstate the worst spot; skipped silently on failure.
        # Europe reads in Celsius.
        clause = ""
        which = "max" if token in ("high-temp", "heat") else ("min" if token in ("low-temp", "cold") else None)
        if which and g["areas"]:
            coords = geocode(sorted(g["areas"])[0])
            if coords:
                t = forecast_temp(coords[0], coords[1], which=which, unit="celsius")
                if t is not None:
                    clause = f" {'Highs' if which == 'max' else 'Lows'} near {t}°C."
        text = f"{opener}{clause} {pick(g['actions'], key + ':a')}"
        tier = "critical" if severity == "Extreme" else ("advisory" if severity == "Moderate" else "serious")
        signals.append(
            Signal(
                category="weather_eu",
                severity=SEVERITY_WEIGHT.get(severity, 60),
                text=text,
                dedup_key=key,
                hashtags=["#WeatherAlert", tag],
                tz=zone,
                tier=tier,
                topic=_eu_topic(token),
                country=f"EU, {tz.country_name(tz.code_for_country(country)) or country_title}",
            )
        )
    return signals


def weather_signals(countries: list[str], min_severity: str = "Severe") -> list[Signal]:
    min_rank = SEVERITY_RANK.get(min_severity, 2)
    return gather(lambda c: _country_signals(c, min_rank), countries)


def active_count(countries: list[str], min_severity: str = "Severe") -> int:
    return len(weather_signals(countries, min_severity))
