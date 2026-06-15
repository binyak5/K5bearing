"""GDACS — Global Disaster Alert and Coordination System (UN OCHA / EC JRC).

Worldwide, keyless multi-hazard feed: tropical cyclones (all basins),
floods, earthquakes, volcanoes, wildfires, droughts. This is what makes
K5Bearing global rather than US/EU-only.

Alert levels: Green (routine) / Orange / Red.
"""
from __future__ import annotations

import requests

from ..config import USER_AGENT
from . import Signal

EVENTS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP"
TIMEOUT = 25

ALERT_RANK = {"Green": 0, "Orange": 1, "Red": 2}
ALERT_WEIGHT = {"Orange": 72, "Red": 92}
ALERT_BADGE = {"Orange": "🟧", "Red": "🟥"}

EVENT_META = {
    "TC": ("🌀", "Tropical Cyclone"),
    "FL": ("🌊", "Flood"),
    "EQ": ("🌐", "Earthquake"),
    "VO": ("🌋", "Volcano"),
    "WF": ("🔥", "Wildfire"),
    "TS": ("🌊", "Tsunami"),
    "DR": ("🌵", "Drought"),
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

        emoji, label = EVENT_META.get(etype, ("⚠️", etype or "Hazard"))
        country = p.get("country") or ""
        name = p.get("name") or label
        sev = p.get("severitydata") or {}
        sev_txt = sev.get("severitytext") or ""

        line2 = name if name else f"{label} in {country}"
        detail = f"\n{sev_txt}" if sev_txt else ""
        loc = f" ({country})" if country and country not in name else ""
        text = f"{ALERT_BADGE.get(alert,'⚠️')} {label.upper()}{loc}\n{line2}{detail}"

        eid = p.get("eventid") or name
        signals.append(
            Signal(
                category="global",
                severity=ALERT_WEIGHT.get(alert, 60),
                text=text,
                dedup_key=f"gdacs:{etype}:{eid}:{alert}",
                hashtags=["#K5Bearing", "#GDACS", f"#{label.replace(' ', '')}"],
            )
        )
    return signals


def active_count(event_types: list[str], min_alert: str = "Orange") -> int:
    return len(global_signals(event_types, min_alert))
