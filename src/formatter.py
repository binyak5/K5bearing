"""Assemble final tweet text and build the daily field-readiness digest."""
from __future__ import annotations

from datetime import datetime, timezone

from .sources import Signal
from .sources import swpc, nws, meteoalarm, gdacs

MAX_LEN = 280


def render(signal: Signal) -> str:
    """Append hashtags and clamp to the 280-char limit."""
    tags = " ".join(dict.fromkeys(signal.hashtags))  # de-dupe, keep order
    body = signal.text.rstrip()
    if not tags:
        return body[:MAX_LEN]

    room = MAX_LEN - len(tags) - 1  # 1 for the joining newline
    if len(body) > room:
        body = body[: room - 1].rstrip() + "…"
    return f"{body}\n{tags}"


def daily_digest(cfg: dict) -> Signal:
    """One readiness snapshot: geomagnetic state, compass status, active alerts."""
    kp = swpc.current_kp()
    label, advisory = swpc.compass_status(kp)
    kp_str = f"{kp:.0f}" if kp is not None else "—"

    us = len(nws.weather_signals(cfg["weather"]["events"], cfg["weather"].get("area", "")))
    eu = (
        meteoalarm.active_count(
            cfg["weather_eu"]["countries"], cfg["weather_eu"].get("min_severity", "Severe")
        )
        if cfg.get("weather_eu", {}).get("enabled")
        else 0
    )
    glob = (
        gdacs.active_count(
            cfg["global_hazards"]["event_types"], cfg["global_hazards"].get("min_alert", "Orange")
        )
        if cfg.get("global_hazards", {}).get("enabled")
        else 0
    )
    if us or eu or glob:
        alert_line = f"Alerts active — US:{us} EU:{eu} Global:{glob}."
    else:
        alert_line = "No major severe-weather alerts (US/EU/global)."

    aurora_line = ""
    if cfg.get("aurora", {}).get("enabled") and kp is not None and kp >= cfg["aurora"]["kp_threshold"]:
        aurora_line = "Aurora possible at high latitudes tonight.\n"

    date = datetime.now(timezone.utc).strftime("%d %b")
    text = (
        f"FIELD READINESS — {date} UTC\n"
        f"Geomagnetic: Kp {kp_str}. Compass {label}.\n"
        f"{alert_line}\n"
        f"{aurora_line}"
        f"{advisory}"
    )
    return Signal(
        category="digest",
        severity=10,
        text=text,
        dedup_key=f"digest:{datetime.now(timezone.utc).date().isoformat()}",
        hashtags=["#K5Bearing", "#FieldReady", "#Navigation"],
    )
