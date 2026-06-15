"""US National Weather Service — severe-weather, hurricane, and tornado alerts.

Public GeoJSON API, no key required. Docs: https://www.weather.gov/documentation/services-web-api
"""
from __future__ import annotations

import requests

from ..config import USER_AGENT
from .. import tz
from . import Signal, pick

ALERTS_URL = "https://api.weather.gov/alerts/active"
TIMEOUT = 20

# NWS severity -> rough ranking weight.
SEVERITY_WEIGHT = {"Extreme": 90, "Severe": 75, "Moderate": 55, "Minor": 40}

# How the alert is announced; one is picked per alert for variety.
OPENERS = [
    "{article} {event} is in effect{where}.",
    "{article} {event} has been issued{where}.",
    "{article} {event} is now active{where}.",
]

# Flowing safety guidance per event type. Each event has a few vetted phrasings;
# one is chosen deterministically per alert so the feed never reads copy-pasted.
ACTIONS = {
    "Tornado Warning": [
        "Move to the lowest floor and an interior room away from windows, and stay there until the warning is lifted.",
        "Get to a basement or a small interior room on the lowest floor now, and stay clear of windows until it passes.",
    ],
    "Hurricane Warning": [
        "Destructive winds and storm surge are expected, so finish your preparations now and follow any evacuation orders without delay.",
        "Life-threatening winds and surge are on the way, so complete your storm prep and leave at once if you are told to evacuate.",
    ],
    "Hurricane Watch": [
        "Hurricane conditions are possible within about two days, so get your preparations in order and monitor official updates closely.",
        "A hurricane may strike within roughly 48 hours, so ready your supplies and keep an eye on the latest forecasts.",
    ],
    "Tropical Storm Warning": [
        "Tropical storm force winds are expected, so secure anything loose outside and stay indoors as conditions deteriorate.",
        "Strong tropical winds are on the way, so tie down loose items and head inside before the weather turns.",
    ],
    "Tsunami Warning": [
        "Move to high ground or inland right away and remain there until officials confirm it is safe to return.",
        "Head for high ground or move well inland immediately, and do not return until authorities give the all clear.",
    ],
    "Blizzard Warning": [
        "Travel will become dangerous in near zero visibility, so stay off the roads and remain somewhere warm.",
        "Whiteout conditions are expected, so avoid all travel and keep warm clothing and supplies within reach.",
    ],
    "Extreme Wind Warning": [
        "Extreme winds are about to arrive, so move to the lowest floor and stay clear of windows until they pass.",
        "Violent winds are imminent, so shelter on the lowest floor away from windows right now.",
    ],
    "Severe Thunderstorm Warning": [
        "Damaging winds and large hail are likely, so head indoors and keep away from windows until the storm moves through.",
        "Strong winds and hail are on the way, so get inside, stay off the road, and wait for the storm to pass.",
    ],
    "Flash Flood Warning": [
        "Water can rise very quickly, so move to higher ground and never try to drive or walk through floodwater.",
        "Flooding can hit within minutes, so climb to higher ground now and never enter water flowing across a road.",
    ],
    "Flood Warning": [
        "Flooding is already underway, so avoid low lying roads and do not drive through water of unknown depth.",
        "Waters are rising, so steer clear of low lying areas and turn around rather than crossing a flooded road.",
    ],
    "Red Flag Warning": [
        "Conditions are right for fire to spread fast, so avoid anything that could throw a spark and be ready to leave at short notice.",
        "Any fire could grow rapidly today, so hold off on open flames and keep an evacuation plan ready.",
    ],
    "Fire Warning": [
        "An active fire is threatening the area, so be ready to evacuate immediately and follow the instructions of local officials.",
        "A fire is bearing down on the area, so prepare to leave at once and do exactly as local officials direct.",
    ],
    "Gale Warning": [
        "Gale force winds and rough seas are expected, so small craft should stay in port and larger vessels should secure for heavy weather.",
        "Gale conditions are building at sea, so keep small boats ashore and rig larger vessels for heavy weather.",
    ],
    "Storm Warning": [
        "Storm force winds are expected at sea, so remain in port and keep well clear of exposed and open water.",
        "Dangerous storm force winds are building offshore, so stay in harbour and avoid open water.",
    ],
    "Special Marine Warning": [
        "Sudden strong winds and dangerous seas are bearing down on the area, so head for harbour and secure your vessel now.",
        "A burst of strong winds and rough seas is moving in, so make for shelter and tie down your vessel right away.",
    ],
    "High Surf Warning": [
        "Large and powerful surf is striking the coast, so stay off rocks, jetties, and the beach face.",
        "Dangerous breakers are hitting the shore, so keep well back from jetties, rocks, and the water's edge.",
    ],
    "Rip Current Statement": [
        "Dangerous rip currents are running along the coast, so swim near a lifeguard and never fight the current if you are caught.",
        "Strong rip currents are likely at the beach, so stay near a lifeguard and swim parallel to shore to break free of one.",
    ],
    "Coastal Flood Warning": [
        "Coastal flooding is expected around high tide, so move vehicles to higher ground and stay off flooded roads.",
        "Tidal flooding is likely along the coast, so relocate vehicles early and avoid roads near the water.",
    ],
    "Winter Storm Warning": [
        "Heavy snow and ice are expected, so avoid travel and keep warm clothing and supplies within reach.",
        "A significant winter storm is moving in, so postpone travel and stock up on warmth and supplies.",
    ],
    "Ice Storm Warning": [
        "Significant ice is expected to build up, so stay off the roads and prepare for downed limbs and power cuts.",
        "A damaging glaze of ice is on the way, so avoid driving and be ready for outages and falling branches.",
    ],
    "Extreme Cold Warning": [
        "Dangerously cold air is moving in, so limit time outdoors and cover exposed skin to guard against frostbite.",
        "Bitter, dangerous cold is settling in, so stay inside where you can and bundle up against frostbite.",
    ],
    "Extreme Heat Warning": [
        "Dangerous heat is building, so stay hydrated, find cool air, and check on anyone at risk.",
        "A dangerous heat wave is setting in, so drink plenty of water, seek cool spaces, and look out for the vulnerable.",
    ],
    "High Wind Warning": [
        "Damaging winds are expected, so secure loose objects and watch for downed limbs and power lines.",
        "Strong, damaging gusts are on the way, so tie down loose items and steer clear of fallen lines.",
    ],
    "Dust Storm Warning": [
        "A wall of blowing dust is dropping visibility to near zero, so pull off the road, turn your lights off, and wait it out.",
        "Blinding dust is cutting visibility to nothing, so leave the roadway, switch off your lights, and stay put.",
    ],
    "Avalanche Warning": [
        "Dangerous avalanche conditions exist in the backcountry, so stay well clear of avalanche terrain and check the local forecast.",
        "The avalanche danger is high in the backcountry, so avoid steep slopes and consult the local avalanche centre.",
    ],
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
        opener = pick(OPENERS, key + ":o").format(article=article, event=event_l, where=where)
        action = pick(ACTIONS.get(event, []), key + ":a")
        text = f"{opener} {action}".strip()

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
