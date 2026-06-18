"""US National Weather Service — severe-weather, hurricane, and tornado alerts.

Public GeoJSON API, no key required. Docs: https://www.weather.gov/documentation/services-web-api
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

from ..config import USER_AGENT
from .. import tz
from . import Signal, pick, region_list


def _parse_dt(s: str):
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None

ALERTS_URL = "https://api.weather.gov/alerts/active"
TIMEOUT = 20

# NWS severity -> rough ranking weight.
SEVERITY_WEIGHT = {"Extreme": 90, "Severe": 75, "Moderate": 55, "Minor": 40}

# How the alert is announced; one is picked per alert for variety.
OPENERS = [
    "{article} {event} is active{where}.",
    "{article} {event} has been issued{where}.",
    "{article} {event} is now active{where}.",
]

# Flowing safety guidance per event type. Each event has a few vetted phrasings;
# one is chosen deterministically per alert so the feed never reads copy-pasted.
ACTIONS = {
    "Tornado Warning": [
        "Move to the lowest floor and an interior room away from windows. Stay there until the warning is lifted.",
        "Get to a basement or an interior room on the lowest floor now and stay clear of windows, as a tornado can drop fast from the wall cloud.",
    ],
    "Hurricane Warning": [
        "Destructive winds and storm surge are expected. Finish your safety plans now and follow any evacuation orders without delay.",
        "Life-threatening winds and surge are on the way. Complete your storm prep and leave now if you are told to evacuate.",
    ],
    "Hurricane Watch": [
        "Hurricane conditions are possible within about two days. Get your preparations in order and monitor official updates closely.",
        "A hurricane may strike within roughly 48 hours. Ready your supplies and keep watch on the latest forecasts.",
    ],
    "Tropical Storm Warning": [
        "Tropical storm-force winds are expected. Secure anything loose outside and stay indoors as conditions worsen.",
        "Tropical storm-force winds are on the way. Tie down loose items and head inside before the weather turns rough.",
    ],
    "Tsunami Warning": [
        "Move to high ground or inland right away. Stay there until officials confirm it is safe to return.",
        "Head for high ground or move well inland immediately. Do not return until authorities give the all clear.",
    ],
    "Blizzard Warning": [
        "Conditions will turn severe in near zero visibility. Stay off the roads and remain somewhere warm.",
        "Blowing snow will bring ground blizzard whiteouts. Avoid all travel and keep warm clothing and supplies within reach.",
    ],
    "Extreme Wind Warning": [
        "Extreme winds are about to arrive. Move to the lowest floor and stay clear of windows until they pass.",
        "Violent winds are imminent. Shelter on the lowest floor away from windows right now.",
    ],
    "Severe Thunderstorm Warning": [
        "Damaging winds and large hail are likely. Head indoors and keep away from windows until the storm moves through.",
        "A supercell can bring damaging winds and large hail. Get inside, stay off the road, and wait for it to pass.",
    ],
    "Flash Flood Warning": [
        "Water can rise very quickly. Move to higher ground and don't try to drive or walk through floodwater.",
        "The flash-flood crest can arrive within minutes. Climb to higher ground now and never enter water flowing across a road.",
    ],
    "Flood Warning": [
        "Flooding is already underway. Avoid low lying roads and do not drive through water of unknown depth.",
        "Waters are rising. Steer clear of low lying areas and turn around instead of crossing a flooded road.",
    ],
    "Red Flag Warning": [
        "Conditions are set for fire to spread fast. Avoid anything that could kick off a blaze and be ready to leave at short notice.",
        "Any fire could grow rapidly today. Hold off on open flames and keep an evacuation plan ready.",
    ],
    "Fire Warning": [
        "An active fire is threatening the area. Be ready to evacuate immediately and follow the instructions of local officials.",
        "An active fire is bearing down on the area. Prepare to leave at once and do exactly as local officials direct.",
    ],
    "Storm Surge Warning": [
        "Life-threatening flooding from rising ocean water is expected. Follow evacuation orders and move inland to higher ground.",
        "A severe surge of seawater is set to overrun the coast. Heed evacuation orders and get to higher ground inland.",
    ],
    "Storm Surge Watch": [
        "Life-threatening coastal flooding from surge is possible. Review your evacuation plan and monitor official updates.",
        "Severe surge flooding may develop along the coast. Ready your evacuation plan and track the latest alerts.",
    ],
    "Hurricane Force Wind Warning": [
        "Hurricane force winds above 64 knots are expected at sea. Remain in port and keep all vessels well clear of open water.",
        "Winds of hurricane force are expected offshore. Stay in harbour and keep every vessel battened down and clear of exposed water.",
    ],
    "Hurricane Force Wind Watch": [
        "Hurricane force winds are possible at sea. Monitor advisories closely and prepare to keep vessels in port.",
        "Winds of hurricane force may develop offshore. Watch the alerts and be ready to stay in harbour.",
    ],
    "Gale Warning": [
        "Gale force winds and rough seas are expected. Small craft should stay in port and larger vessels should secure for heavy weather.",
        "Gale conditions are building at sea. Keep small boats ashore and rig larger vessels for heavy weather.",
    ],
    "Gale Watch": [
        "Gale force winds are possible at sea. Monitor the forecast and prepare to secure your vessel.",
        "Gale conditions may develop offshore. Watch the forecast and ready your vessel for heavy weather.",
    ],
    "Storm Warning": [
        "Storm force winds are expected at sea. Remain in port and keep well clear of exposed and open water.",
        "Storm force winds are building offshore. Make for port and stay off open water until it blows through.",
    ],
    "Storm Watch": [
        "Storm force winds are possible at sea. Track the forecast and prepare to stay in port.",
        "Storm force conditions may build offshore. Follow the forecast and be ready to remain in harbour.",
    ],
    "Hazardous Seas Warning": [
        "Severe, steep and high seas are expected. Mariners should remain in port until conditions improve.",
        "Hazardous seas are building. Keep vessels in port and off the water until the swell eases.",
    ],
    "Special Marine Warning": [
        "Sudden strong winds and severe seas are bearing down on the area. Head for harbour and secure your vessel now.",
        "A squall of strong winds and rough seas is moving in. Make for the nearest harbour and secure for heavy weather.",
    ],
    "Small Craft Advisory": [
        "Winds and seas are rough enough to endanger small boats. Inexperienced mariners and small craft should stay in port.",
        "Conditions are hazardous for small vessels. Small craft should remain in harbour until the advisory ends.",
    ],
    "Heavy Freezing Spray Warning": [
        "Heavy freezing spray will coat vessels in severe icing. Keep decks clear and consider staying in port.",
        "Rapid ice build-up from freezing spray is expected at sea. Clear decks often and stay in port if you can.",
    ],
    "Freezing Spray Advisory": [
        "Freezing spray will coat vessels in ice. Clear it regularly and take care moving about the deck.",
        "Ice from freezing spray is likely on deck and rigging. Clear it often and watch your footing.",
    ],
    "High Surf Warning": [
        "Large and powerful surf is striking the coast. Stay off rocks, seawalls, and the beach face.",
        "Severe breakers are hitting the shore. Keep well back from seawalls, rocks, and the water's edge.",
    ],
    "High Surf Advisory": [
        "Large breaking waves are expected along the coast. Use caution near the surf and stay off rocks and seawalls.",
        "Elevated surf is on the way. Keep clear of the waterline, seawalls, and exposed rocks.",
    ],
    "Rip Current Statement": [
        "Severe rip currents are running along the coast. Swim near a lifeguard and never fight the current if you are caught.",
        "Strong rip currents are likely at the beach. Stay near a lifeguard and swim parallel to shore to break free of one.",
    ],
    "Beach Hazards Statement": [
        "Hazardous conditions such as rip currents or sneaker waves are expected at the beach. Stay alert and heed lifeguard guidance.",
        "Severe surf and currents are possible at the beach. Keep a close eye on the water and follow lifeguard advice.",
    ],
    "Coastal Flood Warning": [
        "Coastal flooding is expected around high tide. Move vehicles to higher ground and stay off flooded roads.",
        "Tidal flooding is likely along the coast. Relocate vehicles early and avoid roads near the water.",
    ],
    "Coastal Flood Watch": [
        "Coastal flooding is possible around high tide. Monitor alerts and be ready to move vehicles to higher ground.",
        "Tidal flooding may develop along the coast. Watch the forecast and prepare to relocate vehicles early.",
    ],
    "Coastal Flood Advisory": [
        "Shallow coastal flooding is expected around high tide. Avoid flooded roads near the shore.",
        "Some tidal flooding is likely near the coast. Steer clear of low roads close to the water.",
    ],
    "Lakeshore Flood Warning": [
        "Flooding is expected along the lakeshore. Move vehicles to higher ground and stay off flooded roads.",
        "Lakeshore flooding is underway. Relocate vehicles and avoid roads near the water.",
    ],
    "Tsunami Advisory": [
        "Strong currents and severe waves are expected for anyone in or near the water. Leave the water and stay off the beach.",
        "Severe currents and surges are expected at the coast. Get out of the water and keep off the beach and harbours.",
    ],
    "Tsunami Watch": [
        "A distant earthquake may trigger a tsunami. Keep an eye on official alerts and be ready to move to high ground.",
        "A tsunami is possible after a distant quake. Monitor official alerts and be ready to head for high ground.",
    ],
    "Winter Storm Warning": [
        "Heavy snow and ice are expected. Avoid travel and keep warm clothing and supplies within reach.",
        "A heavy-hitting winter storm is moving in. Postpone travel and stock up on warmth and supplies.",
    ],
    "Ice Storm Warning": [
        "Heavy ice is expected to build up. Stay off the roads and prepare for downed limbs and power cuts.",
        "A damaging glaze of ice is on the way. Avoid driving and be ready for outages and falling branches.",
    ],
    "Extreme Cold Warning": [
        "A severe wind chill is setting in. Limit time outdoors and cover exposed skin to guard against frostbite.",
        "Bitter wind chill is settling in. Stay inside where you can and guard against frostbite.",
    ],
    "Extreme Heat Warning": [
        "Severe heat is building. Stay hydrated, find cool air, and check on anyone at risk.",
        "A severe heat wave is setting in. Drink plenty of water, seek cool spaces, and look out for the vulnerable.",
    ],
    "High Wind Warning": [
        "Violent winds are expected. Secure loose objects and watch for downed limbs and power lines.",
        "Strong gusts are on the way. Tie down loose items and steer clear of fallen lines.",
    ],
    "Dust Storm Warning": [
        "A wall of blowing dust is dropping visibility to near zero. Pull off the road, turn your lights off, and wait it out.",
        "Blinding dust is cutting visibility to nothing. Leave the roadway, switch off your lights, and stay put.",
    ],
    "Avalanche Warning": [
        "Severe avalanche conditions exist in the backcountry. Stay well clear of avalanche terrain and check the local forecast.",
        "The avalanche danger is high in the backcountry. Avoid steep slopes and check the local avalanche forecast.",
    ],
    "Flood Advisory": [
        "Minor flooding of low-lying and poor-drainage areas is expected. Avoid the usual problem spots and never drive through standing water.",
        "Nuisance flooding is likely in low spots. Give yourself extra time and steer around any water across the road.",
    ],
    "Wind Advisory": [
        "Strong winds are expected. Secure light objects outside and take care driving high-profile vehicles.",
        "Gusty winds are on the way. Tie down loose items and watch for sudden crosswinds on the road.",
    ],
    "Heat Advisory": [
        "Hot and humid conditions are expected. Drink plenty of water, take breaks in the shade, and check on those at risk.",
        "Severe heat is building. Stay hydrated, limit strenuous activity, and never leave anyone in a parked vehicle.",
    ],
    "Winter Weather Advisory": [
        "Snow, sleet, or ice will make roads slick. Slow down, allow extra distance, and travel only if you need to.",
        "A wintry mix is expected to make travel hazardous. Take it slow and keep an eye on changing conditions.",
    ],
    "Dense Fog Advisory": [
        "Dense fog is cutting visibility to a quarter mile or less. Slow down, use low-beam headlights, and leave extra room.",
        "Thick fog is making driving conditions severe. Reduce speed, switch to low beams, and watch for slow or stopped traffic.",
    ],
    "Freeze Warning": [
        "Sub-freezing temperatures are expected. Protect tender plants, pets, and any exposed pipes overnight.",
        "A hard freeze is on the way. Cover sensitive plants, bring pets inside, and guard against burst pipes.",
    ],
    "Air Quality Alert": [
        "Air pollution is reaching unhealthy levels. Limit time outdoors, keep windows closed, and take it easy if you have breathing trouble.",
        "Poor air quality is expected. Reduce outdoor activity and consider a mask if you are sensitive to pollution.",
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
    "Storm Surge Warning": "#StormSurge",
    "Storm Surge Watch": "#StormSurge",
    "Hurricane Force Wind Warning": "#Marine",
    "Hurricane Force Wind Watch": "#Marine",
    "Gale Warning": "#Marine",
    "Gale Watch": "#Marine",
    "Storm Warning": "#Marine",
    "Storm Watch": "#Marine",
    "Hazardous Seas Warning": "#Marine",
    "Special Marine Warning": "#Marine",
    "Small Craft Advisory": "#Marine",
    "Heavy Freezing Spray Warning": "#Marine",
    "Freezing Spray Advisory": "#Marine",
    "High Surf Warning": "#HighSurf",
    "High Surf Advisory": "#HighSurf",
    "Rip Current Statement": "#RipCurrent",
    "Beach Hazards Statement": "#BeachSafety",
    "Coastal Flood Warning": "#CoastalFlood",
    "Coastal Flood Watch": "#CoastalFlood",
    "Coastal Flood Advisory": "#CoastalFlood",
    "Lakeshore Flood Warning": "#Flood",
    "Tsunami Advisory": "#Tsunami",
    "Tsunami Watch": "#Tsunami",
    "Winter Storm Warning": "#WinterStorm",
    "Ice Storm Warning": "#IceStorm",
    "Extreme Cold Warning": "#ExtremeCold",
    "Extreme Heat Warning": "#ExtremeHeat",
    "High Wind Warning": "#HighWind",
    "Dust Storm Warning": "#DustStorm",
    "Avalanche Warning": "#Avalanche",
    "Flood Advisory": "#Flood",
    "Wind Advisory": "#Wind",
    "Heat Advisory": "#Heat",
    "Winter Weather Advisory": "#WinterWeather",
    "Dense Fog Advisory": "#Fog",
    "Freeze Warning": "#Freeze",
    "Air Quality Alert": "#AirQuality",
}



# Advisories (anything ending in "Advisory") get the calm "Heads up," lead;
# everything else, including these life-threatening events, posts as written.
# The "critical" tag is kept for ranking/clarity though it no longer alters text.
CRITICAL_EVENTS = {
    "Tornado Warning", "Hurricane Warning", "Tsunami Warning",
    "Extreme Wind Warning", "Storm Surge Warning",
    "Hurricane Force Wind Warning", "Flash Flood Warning", "Fire Warning",
}


def _tier(event: str) -> str:
    if event in CRITICAL_EVENTS:
        return "critical"
    if event.endswith("Advisory"):
        return "advisory"
    return "serious"


def _topic(event: str) -> str:
    """Coarse subject for the no-repeat-in-a-row rule (shared vocab with EU)."""
    e = event.lower()
    if "tornado" in e:
        return "tornado"
    if "tsunami" in e:
        return "tsunami"
    if "flood" in e or "surge" in e:
        return "flood"
    if "hurricane" in e or "tropical" in e:
        return "tropical"
    if "thunderstorm" in e:
        return "thunderstorm"
    if "fire" in e or "red flag" in e:
        return "fire"
    if "snow" in e or "blizzard" in e or "ice" in e or "winter" in e or "freez" in e:
        return "winter"
    if "heat" in e:
        return "heat"
    if "cold" in e or "chill" in e:
        return "cold"
    if "dust" in e:
        return "dust"
    if "avalanche" in e:
        return "avalanche"
    if "fog" in e:
        return "fog"
    if "air quality" in e:
        return "air"
    if any(w in e for w in ("surf", "rip current", "seas", "marine", "spray", "gale", "storm", "wind")):
        return "marine" if any(w in e for w in ("surf", "rip", "seas", "marine", "spray", "gale")) else "wind"
    return "weather"

# Small Craft Advisories are extremely common; collapse them all into one
# low-priority roundup per run rather than flooding the feed with each zone.
SCA_ROUNDUP = [
    "Small craft advisories are in effect across {n} US coastal zones. Inexperienced mariners and small craft should stay in port until conditions ease.",
    "Small craft advisories cover {n} stretches of US coastal water. Small craft should remain in harbour until conditions improve.",
]


def _area_label(area_desc: str) -> str:
    """Name the NWS areas ('Centre, PA; Clearfield, PA; ...') as a readable
    list, capped at a sensible length with 'and N other areas' for the rest."""
    return region_list([a.strip() for a in area_desc.split(";") if a.strip()])


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
    now = datetime.now(timezone.utc)
    today = now.date()
    signals: list[Signal] = []
    seen_keys: set[str] = set()
    sca_zones: set[str] = set()

    for feat in data.get("features", []):
        props = feat.get("properties", {})
        event = props.get("event", "")
        if event not in wanted:
            continue

        # Freshness: the active feed is already non-expired; also drop alerts
        # that don't take effect until a future day (keep ones in effect today).
        onset = _parse_dt(props.get("onset") or props.get("effective"))
        if onset is not None and onset.astimezone(timezone.utc).date() > today:
            continue

        area_desc = props.get("areaDesc", "")
        # Small Craft Advisories are too numerous to post individually; just
        # tally the distinct zones and emit one roundup after the loop.
        if event == "Small Craft Advisory":
            sca_zones.add(area_desc[:60])
            continue

        # Collapse many simultaneous warnings of the same type+area into one post.
        key = f"weather:{event}:{area_desc[:60]}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        severity = SEVERITY_WEIGHT.get(props.get("severity", ""), 50)
        label = _area_label(area_desc)
        event_l = event.lower()
        article = "An" if event_l[:1] in "aeiou" else "A"
        # State the country (these are all US alerts); mirrors the European
        # "... in {country}" pattern.
        where = f" for {label} in the US" if label else " in the US"
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
                tier=_tier(event),
                topic=_topic(event),
            )
        )

    # One low-priority roundup for all Small Craft Advisories, capped to a
    # single post per dedup window so they can never flood the feed.
    if sca_zones:
        rkey = "weather:sca-roundup"
        signals.append(
            Signal(
                category="weather",
                severity=50,  # un-boosted: only posts when nothing serious is active
                text=pick(SCA_ROUNDUP, rkey).format(n=len(sca_zones)),
                dedup_key=rkey,
                hashtags=["#Marine", "#WeatherAlert"],
                tz=None,  # spans many zones -> UTC
                tier="advisory",
                topic="marine",
            )
        )
    return signals
