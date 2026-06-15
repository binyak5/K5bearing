"""US National Weather Service — severe-weather, hurricane, and tornado alerts.

Public GeoJSON API, no key required. Docs: https://www.weather.gov/documentation/services-web-api
"""
from __future__ import annotations

import requests

from ..config import USER_AGENT
from .. import tz
from . import Signal

ALERTS_URL = "https://api.weather.gov/alerts/active"
TIMEOUT = 20

# NWS severity -> rough ranking weight.
SEVERITY_WEIGHT = {"Extreme": 90, "Severe": 75, "Moderate": 55, "Minor": 40}

# Flowing safety guidance per event type, written as full advisory sentences.
ACTIONS = {
    "Tornado Warning": "Move to the lowest floor and an interior room away from windows, and stay there until the warning is lifted.",
    "Hurricane Warning": "Destructive winds and storm surge are expected, so finish your preparations now and follow any evacuation orders without delay.",
    "Hurricane Watch": "Hurricane conditions are possible within about two days, so get your preparations in order and monitor official updates closely.",
    "Tropical Storm Warning": "Tropical storm force winds are expected, so secure anything loose outside and stay indoors as conditions deteriorate.",
    "Tsunami Warning": "Move to high ground or inland right away and remain there until officials confirm it is safe to return.",
    "Blizzard Warning": "Travel will become dangerous in near zero visibility, so stay off the roads and remain somewhere warm.",
    "Extreme Wind Warning": "Extreme winds are about to arrive, so move to the lowest floor and stay clear of windows until they pass.",
    "Severe Thunderstorm Warning": "Damaging winds and large hail are likely, so head indoors and keep away from windows until the storm moves through.",
    "Flash Flood Warning": "Water can rise very quickly, so move to higher ground and never try to drive or walk through floodwater.",
    "Flood Warning": "Flooding is already underway, so avoid low lying roads and do not drive through water of unknown depth.",
    "Red Flag Warning": "Conditions are right for fire to spread fast, so avoid anything that could throw a spark and be ready to leave at short notice.",
    "Fire Warning": "An active fire is threatening the area, so be ready to evacuate immediately and follow the instructions of local officials.",
    "Gale Warning": "Gale force winds and rough seas are expected, so small craft should stay in port and larger vessels should secure for heavy weather.",
    "Storm Warning": "Storm force winds are expected at sea, so remain in port and keep well clear of exposed and open water.",
    "Special Marine Warning": "Sudden strong winds and dangerous seas are bearing down on the area, so head for harbour and secure your vessel now.",
    "High Surf Warning": "Large and powerful surf is striking the coast, so stay off rocks, jetties, and the beach face.",
    "Rip Current Statement": "Dangerous rip currents are running along the coast, so swim near a lifeguard and never fight the current if you are caught.",
    "Coastal Flood Warning": "Coastal flooding is expected around high tide, so move vehicles to higher ground and stay off flooded roads.",
    "Winter Storm Warning": "Heavy snow and ice are expected, so avoid travel and keep warm clothing and supplies within reach.",
    "Ice Storm Warning": "Significant ice is expected to build up, so stay off the roads and prepare for downed limbs and power cuts.",
    "Extreme Cold Warning": "Dangerously cold air is moving in, so limit time outdoors and cover exposed skin to guard against frostbite.",
    "Extreme Heat Warning": "Dangerous heat is building, so stay hydrated, find cool air, and check on anyone at risk.",
    "High Wind Warning": "Damaging winds are expected, so secure loose objects and watch for downed limbs and power lines.",
    "Dust Storm Warning": "A wall of blowing dust is dropping visibility to near zero, so pull off the road, turn your lights off, and wait it out.",
    "Avalanche Warning": "Dangerous avalanche conditions exist in the backcountry, so stay well clear of avalanche terrain and check the local forecast.",
}

# Primary hashtag per event type (a generic #WeatherAlert is always appended).
TAGS = {
    "Tornado Warning": "#Tornado",
    "Hurricane Warning": "#Hurricane",
    "Hurricane Watch": "#Hurricane",
    "Tropical Storm Warning": "#TropicalStorm",
    "Tsunami Warning": "#Tsunami",
    "Blizzard Warning": "#Blizzard",
    "Extreme Wind Warning": "#Wind",
    "Severe Thunderstorm Warning": "#Storm",
    "Flash Flood Warning": "#Flood",
    "Flood Warning": "#Flood",
    "Red Flag Warning": "#FireWeather",
    "Fire Warning": "#Wildfire",
    "Gale Warning": "#Marine",
    "Storm Warning": "#Marine",
    "Special Marine Warning": "#Marine",
    "High Surf Warning": "#HighSurf",
    "Rip Current Statement": "#RipCurrent",
    "Coastal Flood Warning": "#CoastalFlood",
    "Winter Storm Warning": "#WinterStorm",
    "Ice Storm Warning": "#IceStorm",
    "Extreme Cold Warning": "#ExtremeCold",
    "Extreme Heat Warning": "#ExtremeHeat",
    "High Wind Warning": "#HighWind",
    "Dust Storm Warning": "#DustStorm",
    "Avalanche Warning": "#Avalanche",
}


def _area_label(area_desc: str) -> str:
    """Condense NWS areaDesc ('Centre, PA; Clearfield, PA; ...') to prose."""
    areas = [a.strip() for a in area_desc.split(";") if a.strip()]
    if not areas:
        return ""
    if len(areas) == 1:
        return areas[0]
    if len(areas) == 2:
        return f"{areas[0]} and {areas[1]}"
    return f"{areas[0]} and {len(areas) - 1} other areas"


def weather_signals(events: list[str], area: str = "") -> list[Signal]:
    params = {"status": "actual", "message_type": "alert"}
    if area:
        params["area"] = area
    try:
        resp = requests.get(
            ALERTS_URL,
            headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
            params=params,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return []

    wanted = set(events)
    signals: list[Signal] = []
    seen_keys: set[str] = set()

    for feat in data.get("features", []):
        props = feat.get("properties", {})
        event = props.get("event", "")
        if event not in wanted:
            continue

        area_desc = props.get("areaDesc", "")
        # Collapse many simultaneous warnings of the same type+area into one post.
        key = f"weather:{event}:{area_desc[:60]}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        severity = SEVERITY_WEIGHT.get(props.get("severity", ""), 50)
        label = _area_label(area_desc)
        event_l = event.lower()
        article = "An" if event_l[:1] in "aeiou" else "A"
        where = f" for {label}" if label else ""
        text = f"{article} {event_l} is in effect{where}."
        action = ACTIONS.get(event, "")
        if action:
            text += f" {action}"

        centroid = tz.polygon_centroid(feat.get("geometry"))
        zone = tz.zone_for_coords(*centroid) if centroid else None

        signals.append(
            Signal(
                category="weather",
                severity=severity,
                text=text,
                dedup_key=key,
                hashtags=[TAGS.get(event, "#Weather"), "#WeatherAlert"],
                tz=zone,
            )
        )
    return signals
