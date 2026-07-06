"""Shared alert wording library.

This is the reusable phrasing for severe-weather alerts — openers, per-event
safety guidance, hashtags, ranking weights, and the tier/topic classifiers. It
was originally embedded in the US NWS source; it now lives here so the wording
survives that source's removal and can be reused by the Rotterdam source (and
any future one). WORDING.md documents the full human-facing catalogue (including
the US/EU/Gulf phrasings kept for reference).

Event names are the US NWS labels, kept as stable keys so the wording maps the
same way everywhere. A derived source (e.g. Rotterdam) picks the event whose
guidance best fits the hazard it detected and reuses that phrasing verbatim.
"""
from __future__ import annotations

# NWS severity -> rough ranking weight.
SEVERITY_WEIGHT = {"Extreme": 90, "Severe": 75, "Moderate": 55, "Minor": 40}

# Per-event severity floor for the life-threatening events, so ranking (which is
# pure-severity) always sorts them near the top even when a feed tags them low.
EVENT_FLOOR = {
    "Tornado Warning": 96,
    "Hurricane Warning": 96,
    "Storm Surge Warning": 95,
    "Extreme Wind Warning": 95,
    "Hurricane Force Wind Warning": 95,
    "Fire Warning": 88,
    "Flash Flood Warning": 84,
    "Severe Thunderstorm Warning": 82,
    "Storm Warning": 86,
    "Hazardous Seas Warning": 82,
    "Special Marine Warning": 80,
    "Gale Warning": 74,
}

# How the alert is announced; one is picked per alert for variety.
OPENERS = [
    "{article} {event} is active{where}.",
    "{article} {event} has been issued{where}.",
]

# Flowing safety guidance per event type. One phrasing per event (chosen
# deterministically per alert when more than one is listed).
ACTIONS = {
    "Tornado Warning": [
        "Get to a basement or an interior room on the lowest floor and keep clear of windows. Stay there until the warning is lifted.",
    ],
    "Hurricane Warning": [
        "Destructive winds and storm surge are expected. Follow any evacuation orders.",
        "Life-threatening winds and surge are on the way. Follow any evacuation orders.",
    ],
    "Hurricane Watch": [
        "Hurricane conditions are possible within about two days. Keep a close watch on the latest alerts.",
        "A hurricane may strike within roughly 48 hours. Keep a close watch on the latest alerts.",
    ],
    "Tropical Storm Warning": [
        "Tropical storm-force winds are expected. Head inside before the weather turns rough.",
        "Tropical storm-force winds are on the way. Head inside before the weather turns rough.",
    ],
    "Blizzard Warning": [
        "Blowing snow will bring ground blizzard whiteouts. Conditions will turn severe in near zero visibility.",
    ],
    "Extreme Wind Warning": [
        "Violent winds are imminent. Stay clear of windows until they pass.",
    ],
    "Severe Thunderstorm Warning": [
        "A supercell can bring damaging winds and large hail. Head indoors and keep away from windows until the storm moves through.",
    ],
    "Flash Flood Warning": [
        "The flash-flood crest can arrive within minutes. Climb to higher ground.",
    ],
    "Flood Warning": [
        "Waters are rising. Steer clear of low lying areas.",
    ],
    "Red Flag Warning": [
        "Conditions are set for fire to spread fast. Avoid anything that could kick off a blaze.",
    ],
    "Fire Warning": [
        "An active fire is threatening the area. Be ready to evacuate immediately.",
    ],
    "Storm Surge Warning": [
        "A severe surge of seawater is set to overrun the coast. Heed evacuation orders and get to higher ground.",
    ],
    "Storm Surge Watch": [
        "Severe surge flooding may develop along the coast. Keep a close watch on the latest alerts.",
    ],
    "Hurricane Force Wind Warning": [
        "Hurricane force winds above 64 knots are expected at sea. Remain in port and keep all vessels well clear of open water.",
    ],
    "Hurricane Force Wind Watch": [
        "Hurricane force winds are possible at sea. Monitor alerts closely and prepare to keep vessels in port.",
    ],
    "Gale Warning": [
        "Gale force winds and rough seas are expected. Small craft should stay in port and rig larger vessels for heavy weather.",
    ],
    "Gale Watch": [
        "Gale force winds are possible at sea. Watch the forecast and ready your vessel for heavy weather.",
    ],
    "Storm Warning": [
        "Storm force winds are building offshore. Remain in port and keep well clear of exposed and open water.",
    ],
    "Hazardous Seas Warning": [
        "Severe, steep and high seas are expected. Keep vessels in port and off the water until the swell eases.",
    ],
    "Special Marine Warning": [
        "Sudden strong winds and severe seas are bearing down on the area. Head for harbour and secure your vessel for heavy weather.",
    ],
    "Heavy Freezing Spray Warning": [
        "Rapid ice build-up from freezing spray is expected at sea. Clear decks often and stay in port if you can.",
    ],
    "High Surf Warning": [
        "Severe breakers are hitting the shore. Keep well back from seawalls, rocks, and the water's edge.",
    ],
    "Rip Current Statement": [
        "Severe rip currents are running along the coast. Swim near a lifeguard and never fight the current if you are caught.",
    ],
    "Coastal Flood Warning": [
        "Tidal flooding is likely along the coast.",
    ],
    "Lakeshore Flood Warning": [
        "Lakeshore flooding is underway. Keep a close watch on the latest alerts.",
    ],
    "Winter Storm Warning": [
        "A heavy-hitting winter storm is moving in. Postpone travel and keep supplies within reach.",
    ],
    "Ice Storm Warning": [
        "Heavy ice is expected to build up. Stay off the roads and prepare for downed limbs and power cuts.",
    ],
    "Extreme Cold Warning": [
        "Bitter wind chill is settling in. Stay inside where you can and guard exposed skin against frostbite.",
    ],
    "Extreme Heat Warning": [
        "A severe heat wave is setting in. Drink plenty of water, seek cool spaces, and look out for the vulnerable.",
    ],
    "High Wind Warning": [
        "Violent winds are expected. Secure loose objects and watch for downed limbs and power lines.",
    ],
    "Dust Storm Warning": [
        "Blinding dust is cutting visibility to nothing. Pull off the road and wait it out.",
    ],
    "Avalanche Warning": [
        "Severe avalanche conditions exist in the backcountry. Stay well clear of avalanche terrain and check the local forecast.",
    ],
    "Freeze Warning": [
        "A hard sub-freeze is on the way. Cover anything frost-sensitive and guard against burst pipes.",
    ],
    "Air Quality Alert": [
        "Air pollution is reaching unhealthy levels. Limit time outdoors, keep windows closed, and take it easy if you have breathing trouble.",
    ],
    # Dense fog has no US NWS "Warning" event (it's an Advisory there); this
    # phrasing is preserved from the European/Gulf fog wording so a derived
    # source can warn on it. Kept here so no wording is lost.
    "Dense Fog Warning": [
        "Dense fog is closing in and visibility is dropping fast. Slow down, switch to low-beam headlights, and watch for sudden slow or stopped traffic.",
    ],
}

# Primary hashtag per event type (a generic #WeatherAlert is always appended).
TAGS = {
    "Tornado Warning": "#Tornado",
    "Hurricane Warning": "#Hurricane",
    "Hurricane Watch": "#Hurricane",
    "Tropical Storm Warning": "#TropicalStorm",
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
    "Hazardous Seas Warning": "#Marine",
    "Special Marine Warning": "#Marine",
    "Heavy Freezing Spray Warning": "#Marine",
    "High Surf Warning": "#HighSurf",
    "Rip Current Statement": "#RipCurrent",
    "Coastal Flood Warning": "#CoastalFlood",
    "Lakeshore Flood Warning": "#Flood",
    "Winter Storm Warning": "#WinterStorm",
    "Ice Storm Warning": "#IceStorm",
    "Extreme Cold Warning": "#ExtremeCold",
    "Extreme Heat Warning": "#ExtremeHeat",
    "High Wind Warning": "#HighWind",
    "Dust Storm Warning": "#DustStorm",
    "Avalanche Warning": "#Avalanche",
    "Freeze Warning": "#Freeze",
    "Air Quality Alert": "#AirQuality",
    "Dense Fog Warning": "#Fog",
}

# Advisories (anything ending in "Advisory") get the calm "Heads up," lead;
# everything else, including these life-threatening events, posts as written.
CRITICAL_EVENTS = {
    "Tornado Warning", "Hurricane Warning", "Tsunami Warning",
    "Extreme Wind Warning", "Storm Surge Warning",
    "Hurricane Force Wind Warning", "Fire Warning",
}


def tier(event: str) -> str:
    if event in CRITICAL_EVENTS:
        return "critical"
    if event.endswith("Advisory"):
        return "advisory"
    return "serious"


def topic(event: str) -> str:
    """Coarse subject for the no-repeat-in-a-row rule."""
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


def severity_for(event: str) -> int:
    """Ranking weight for an event: its floor if it has one, else the Severe
    default. Lets a derived source rank reused events the same way the feeds did."""
    return EVENT_FLOOR.get(event, SEVERITY_WEIGHT["Severe"])
