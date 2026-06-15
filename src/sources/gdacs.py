"""GDACS — Global Disaster Alert and Coordination System (UN OCHA / EC JRC).

Worldwide, keyless multi-hazard feed: tropical cyclones (all basins),
floods, earthquakes, volcanoes, wildfires, droughts. This is what makes
K5Bearing global rather than US/EU-only.

Alert levels: Green (routine) / Orange / Red.
"""
from __future__ import annotations

import requests

from ..config import USER_AGENT
from .. import tz
from . import Signal

EVENTS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP"
TIMEOUT = 25

ALERT_RANK = {"Green": 0, "Orange": 1, "Red": 2}
ALERT_WEIGHT = {"Orange": 72, "Red": 92}

# Event type -> (label, flowing advisory sentence).
EVENT_META = {
    "TC": ("Tropical Cyclone", "This is a dangerous storm, so follow evacuation orders and stay clear of the coast, where storm surge is the deadliest threat."),
    "FL": ("Flood", "Move to higher ground, keep clear of floodwater, and follow the instructions of local authorities."),
    "EQ": ("Earthquake", "Aftershocks are possible, so stay clear of damaged buildings and be ready for further shaking."),
    "VO": ("Volcano", "Follow any exclusion zones and evacuation guidance issued by local authorities."),
    "WF": ("Wildfire", "Stay ready to evacuate at short notice and keep a close watch on local alerts."),
    "TS": ("Tsunami", "Move to high ground or inland immediately and stay there until officials say it is safe."),
    "DR": ("Drought", "Conserve water where you can and follow local guidance."),
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

        label, action = EVENT_META.get(etype, (etype or "Hazard", "Follow local guidance."))
        country = p.get("country") or ""
        name = p.get("name") or label
        sev = p.get("severitydata") or {}
        sev_txt = sev.get("severitytext") or ""

        article = "An" if alert[:1] in "aeiouAEIOU" else "A"
        loc = f" near {country}" if country and country not in name else ""
        detail = f", currently {sev_txt.lower()}" if sev_txt else ""
        text = f"{article} {alert.lower()} alert is in effect for {name}{loc}{detail}. {action}"

        eid = p.get("eventid") or name
        country_tag = "#" + country.replace(" ", "") if country else "#GDACS"
        centroid = tz.polygon_centroid(feat.get("geometry"))
        zone = tz.zone_for_coords(*centroid) if centroid else None
        signals.append(
            Signal(
                category="global",
                severity=ALERT_WEIGHT.get(alert, 60),
                text=text,
                dedup_key=f"gdacs:{etype}:{eid}:{alert}",
                hashtags=["#" + label.replace(" ", ""), country_tag],
                tz=zone,
            )
        )
    return signals


def active_count(event_types: list[str], min_alert: str = "Orange") -> int:
    return len(global_signals(event_types, min_alert))
