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

# Per-event severity floor for the life-threatening events. The NWS feed's own
# severity tag is inconsistent (a tornado warning can come through as "Severe"),
# so since ranking is now pure-severity we floor these so they always sort near
# the top. The event's actual severity is max(feed weight, floor).
EVENT_FLOOR = {
    "Tornado Warning": 96,
    "Hurricane Warning": 96,
    "Storm Surge Warning": 95,
    "Extreme Wind Warning": 95,
    "Hurricane Force Wind Warning": 95,
    "Fire Warning": 88,
    "Flash Flood Warning": 84,
    "Severe Thunderstorm Warning": 82,
    # Official marine warnings, floored to match the modeled marine signals in
    # marine.py so the authoritative product never ranks below the estimate
    # (the NWS feed tags these inconsistently, often "Moderate").
    "Storm Warning": 86,           # storm-force winds at sea (matches marine storm-force)
    "Hazardous Seas Warning": 82,
    "Special Marine Warning": 80,
    "Gale Warning": 74,            # matches marine gale-force
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
        "Move to the lowest floor and an interior room away from windows. Stay there until the warning is lifted.",
        "Get to a basement or an interior room on the lowest floor and stay clear of windows, as a tornado can drop fast from the wall cloud.",
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
    "Blizzard Warning": [
        "Blowing snow will bring ground blizzard whiteouts. Conditions will turn severe in near zero visibility. Stay off the roads and keep supplies within reach.",
    ],
    "Extreme Wind Warning": [
        "Violent winds are imminent. Move to the lowest floor and stay clear of windows until they pass.",
    ],
    "Severe Thunderstorm Warning": [
        "A supercell can bring damaging winds and large hail. Head indoors and keep away from windows until the storm moves through.",
    ],
    "Flash Flood Warning": [
        "The flash-flood crest can arrive within minutes. Climb to higher ground now and don't try to drive or walk through floodwater.",
    ],
    "Flood Warning": [
        "Waters are rising. Steer clear of low lying areas and turn around instead of crossing a flooded road.",
    ],
    "Red Flag Warning": [
        "Conditions are set for fire to spread fast. Avoid anything that could kick off a blaze and be ready to leave at short notice.",
    ],
    "Fire Warning": [
        "An active fire is threatening the area. Be ready to evacuate immediately and follow the instructions of local officials.",
    ],
    "Storm Surge Warning": [
        "A severe surge of seawater is set to overrun the coast. Heed evacuation orders and get to higher ground inland.",
    ],
    "Storm Surge Watch": [
        "Severe surge flooding may develop along the coast. Ready your evacuation plan and track the latest alerts.",
    ],
    "Hurricane Force Wind Warning": [
        "Hurricane force winds above 64 knots are expected at sea. Remain in port and keep all vessels well clear of open water.",
    ],
    "Hurricane Force Wind Watch": [
        "Hurricane force winds are possible at sea. Monitor advisories closely and prepare to keep vessels in port.",
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
        "Lakeshore flooding is underway. Monitor alerts and be ready to move vehicles to higher ground.",
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
        "Blinding dust is cutting visibility to nothing. Pull off the road, switch off your lights, and wait it out.",
    ],
    "Avalanche Warning": [
        "Severe avalanche conditions exist in the backcountry. Stay well clear of avalanche terrain and check the local forecast.",
    ],
    "Freeze Warning": [
        "A hard sub-freeze is on the way. Cover sensitive plants, bring pets inside, and guard against burst pipes.",
    ],
    "Air Quality Alert": [
        "Air pollution is reaching unhealthy levels. Limit time outdoors, keep windows closed, and take it easy if you have breathing trouble.",
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
}



# Advisories (anything ending in "Advisory") get the calm "Heads up," lead;
# everything else, including these life-threatening events, posts as written.
# The "critical" tag is kept for ranking/clarity though it no longer alters text.
# Flash Flood Warning is deliberately NOT critical: it's high-volume (one per
# affected area on any rainy day) and the +200 critical boost plus the
# same-topic-exemption let it dominate the whole feed. Kept as "serious" so it
# still posts at its severity weight but competes fairly and obeys the
# no-repeat-topic-in-a-row rule.
CRITICAL_EVENTS = {
    "Tornado Warning", "Hurricane Warning", "Tsunami Warning",
    "Extreme Wind Warning", "Storm Surge Warning",
    "Hurricane Force Wind Warning", "Fire Warning",
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
    "Small craft advisories cover {n} stretches of US coastal water. Small craft should remain in harbour until conditions ease.",
]


def _split_state(seg: str) -> tuple[str, str | None]:
    """Split an NWS area segment 'Travis, TX' into ('Travis', 'TX'). Returns
    (segment, None) when the trailing token isn't a US state abbreviation
    (e.g. marine zones like 'Coastal waters out 10 nm')."""
    parts = seg.rsplit(",", 1)
    if len(parts) == 2 and tz.state_name(parts[1].strip()):
        return parts[0].strip(), parts[1].strip().upper()
    return seg.strip(), None


def _area_label(area_desc: str) -> str:
    """Name the NWS areas ('Centre, PA; Clearfield, PA; ...') as a readable
    list, capped at a sensible length with 'and N other areas' for the rest.

    When every county is in one state, that state is already shown in the
    "USA, <state>" geo tag, so we drop the repeated ', ST' from the body list
    ('Travis and Williamson'). Multi-state alerts keep the state for clarity."""
    segs = [a.strip() for a in area_desc.split(";") if a.strip()]
    pairs = [_split_state(s) for s in segs]
    states = {st for _, st in pairs if st}
    names = [place for place, _ in pairs] if len(states) == 1 else segs
    return region_list(names)


def _is_excluded(area_desc: str, excluded: set[str]) -> bool:
    """True if every state/territory the alert covers is in the excluded set, so
    an alert confined to e.g. Puerto Rico is dropped but a mainland alert that
    merely also touches an excluded area is kept."""
    if not excluded:
        return False
    codes = {st for _, st in (_split_state(s) for s in area_desc.split(";")) if st}
    return bool(codes and codes <= excluded)


def _geo_tag(area_desc: str) -> str:
    """The "USA, <state>" geo tag for a US alert. NWS areaDesc lists each county
    as 'County, ST', so we read the state from the first segment that has one and
    spell it out. Falls back to plain "USA" (e.g. marine zones with no state)."""
    for seg in area_desc.split(";"):
        _, st = _split_state(seg)
        if st:
            return f"USA, {tz.state_name(st)}"
    return "USA"


def weather_signals(events: list[str], area: str = "", exclude: list[str] | None = None) -> list[Signal]:
    params = {"status": "actual", "message_type": "alert"}
    if area:
        params["area"] = area
    # State/territory codes to drop (e.g. PR, GU). An alert is skipped only when
    # every area it covers is excluded, so a multi-area mainland alert is kept.
    excluded = {c.upper() for c in (exclude or [])}
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
        # Drop alerts confined to excluded states/territories (e.g. PR, GU).
        if _is_excluded(area_desc, excluded):
            continue
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

        severity = max(SEVERITY_WEIGHT.get(props.get("severity", ""), 50), EVENT_FLOOR.get(event, 0))
        label = _area_label(area_desc)
        event_l = event.lower()
        article = "An" if event_l[:1] in "aeiou" else "A"
        # The location (always US here) now rides in the timestamp prefix as
        # "USA, <state>", so it's no longer repeated in the body.
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
                tier=_tier(event),
                topic=_topic(event),
                country=_geo_tag(area_desc),
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
                country="USA",
            )
        )
    return signals
