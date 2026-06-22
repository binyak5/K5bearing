"""GDACS — Global Disaster Alert and Coordination System (UN OCHA / EC JRC).

Worldwide, keyless multi-hazard feed: tropical cyclones (all basins),
floods, earthquakes, volcanoes, wildfires, droughts. This is what makes
K5Bearing global rather than US/EU-only.

Alert levels: Green (routine) / Orange / Red.
"""
from __future__ import annotations

import requests

from ..config import USER_AGENT
from .. import tz, region
from . import Signal, pick

EVENTS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP"
TIMEOUT = 25

ALERT_RANK = {"Green": 0, "Orange": 1, "Red": 2}
ALERT_WEIGHT = {"Orange": 84, "Red": 96}

# How the alert is announced; one is picked per event for variety.
OPENERS = [
    "{article} {alert} alert is active for {name}{loc}{detail}.",
    "{article} {alert} alert has been issued for {name}{loc}{detail}.",
]

# Event type -> (label, list of vetted advisory phrasings).
EVENT_META = {
    "TC": ("Tropical Cyclone", [
        "This is a severe storm, so follow evacuation orders and stay clear of the coast, where storm surge is deadliest.",
        "This is a severe system, so heed evacuation orders and keep away from the coast, where surge poses the greatest risk.",
    ]),
    "FL": ("Flood", [
        "Move to higher ground, keep clear of floodwater, and follow the instructions of local authorities.",
        "Get to higher ground, avoid the floodwater, and do as local authorities advise.",
    ]),
    "EQ": ("Earthquake", [
        "Aftershocks are possible, so stay clear of damaged buildings and be ready for further shaking.",
        "Expect possible aftershocks, so keep away from damaged structures and brace for more movement.",
    ]),
    "VO": ("Volcano", [
        "Respect the exclusion zones and heed evacuation guidance from local authorities.",
    ]),
    "WF": ("Wildfire", [
        "Stay ready to evacuate at short notice and keep a close watch on local alerts.",
    ]),
    "TS": ("Tsunami", [
        "Move to high ground or inland immediately and stay there until officials say it is safe.",
        "Get to high ground or head inland at once, and remain there until the all clear.",
    ]),
    "DR": ("Drought", [
        "Conserve water where you can and follow local guidance.",
        "Use water sparingly and follow the advice of local authorities.",
    ]),
}


def global_signals(event_types: list[str], min_alert: str = "Orange") -> list[Signal]:
    min_rank = ALERT_RANK.get(min_alert, 1)
    wanted = set(event_types)
    try:
        resp = requests.get(EVENTS_URL, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return []

    signals: list[Signal] = []
    for feat in data.get("features", []):
        p = feat.get("properties", {})
        etype = p.get("eventtype")
        alert = p.get("alertlevel", "Green")
        if etype not in wanted or ALERT_RANK.get(alert, 0) < min_rank:
            continue

        centroid = tz.polygon_centroid(feat.get("geometry"))
        if not centroid or not region.in_scope(centroid[1], centroid[0]):
            continue

        label, actions = EVENT_META.get(etype, (etype or "Hazard", ["Follow local guidance."]))
        country = p.get("country") or ""
        name = p.get("name") or label
        sev = p.get("severitydata") or {}
        sev_txt = sev.get("severitytext") or ""

        article = "An" if alert[:1] in "aeiouAEIOU" else "A"
        # Country rides in the "REGION, country" front tag now, not mid-sentence.
        code = region.code_for(centroid[1], centroid[0])
        geo = f"{code}, {country}" if code and country else (code or "")
        loc = ""
        detail = f", currently {sev_txt.lower()}" if sev_txt else ""
        eid = p.get("eventid") or name
        key = f"gdacs:{etype}:{eid}:{alert}"
        opener = pick(OPENERS, key + ":o").format(
            article=article, alert=alert.lower(), name=name, loc=loc, detail=detail
        )
        text = f"{opener} {pick(actions, key + ':a')}"
        country_tag = "#" + country.replace(" ", "") if country else "#GDACS"
        zone = tz.zone_for_coords(*centroid)
        signals.append(
            Signal(
                category="global",
                severity=ALERT_WEIGHT.get(alert, 60),
                text=text,
                dedup_key=key,
                hashtags=["#" + label.replace(" ", ""), country_tag],
                tz=zone,
                tier="critical" if alert == "Red" else "serious",
                country=geo,
                card={
                    "value": f"{alert} ALERT",
                    "event": label,
                    "detail": name,
                    "lat": centroid[1],
                    "lon": centroid[0],
                },
            )
        )
    return signals


def active_count(event_types: list[str], min_alert: str = "Orange") -> int:
    return len(global_signals(event_types, min_alert))
