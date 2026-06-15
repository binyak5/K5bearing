"""K5Bearing entrypoint.

Each invocation:
  1. Collects candidate signals from all enabled sources.
  2. Drops anything already posted (local dedup) or over the daily budget.
  3. Posts the most severe candidates, up to the per-run cap.

Run locally:   DRY_RUN=1 python -m src.main
On CI:         python -m src.main   (with X_* secrets in the environment)
"""
from __future__ import annotations

from .config import load_config
from .state import State
from .formatter import render
from .poster import Poster
from .sources import swpc, nws, meteoalarm, gdacs, aurora, usgs, outdoor, nga, marine, Signal


def collect(cfg: dict) -> list[Signal]:
    signals: list[Signal] = []

    if cfg["geomagnetic"]["enabled"]:
        sig = swpc.geomagnetic_signal(cfg["geomagnetic"]["kp_alert_threshold"])
        if sig:
            signals.append(sig)

    if cfg.get("aurora", {}).get("enabled"):
        sig = aurora.aurora_signal(cfg["aurora"]["kp_threshold"])
        if sig:
            signals.append(sig)

    if cfg["solar"]["enabled"]:
        signals.extend(swpc.solar_signals(cfg["solar"]["watch_prefixes"]))

    if cfg.get("solar_flares", {}).get("enabled"):
        sig = swpc.flare_signal(
            cfg["solar_flares"].get("min_class", "M"),
            cfg["solar_flares"].get("max_age_hours", 6),
        )
        if sig:
            signals.append(sig)

    if cfg.get("radiation", {}).get("enabled"):
        sig = swpc.radiation_signal(cfg["radiation"].get("min_scale", 1))
        if sig:
            signals.append(sig)

    if cfg["weather"]["enabled"]:
        signals.extend(
            nws.weather_signals(cfg["weather"]["events"], cfg["weather"].get("area", ""))
        )

    if cfg.get("weather_eu", {}).get("enabled"):
        signals.extend(
            meteoalarm.weather_signals(
                cfg["weather_eu"]["countries"],
                cfg["weather_eu"].get("min_severity", "Severe"),
            )
        )

    if cfg.get("marine_seas", {}).get("enabled"):
        areas = cfg["marine_seas"].get("areas", [])
        signals.extend(
            marine.sea_signals(areas, cfg["marine_seas"].get("wave_height_threshold", 4.0))
        )
        signals.extend(
            marine.fog_signals(areas, cfg["marine_seas"].get("fog_visibility_m", 1000))
        )

    if cfg.get("maritime_security", {}).get("enabled"):
        signals.extend(
            nga.warning_signals(cfg["maritime_security"].get("categories", []))
        )

    if cfg.get("global_hazards", {}).get("enabled"):
        signals.extend(
            gdacs.global_signals(
                cfg["global_hazards"]["event_types"],
                cfg["global_hazards"].get("min_alert", "Orange"),
            )
        )

    if cfg.get("earthquakes", {}).get("enabled"):
        signals.extend(
            usgs.quake_signals(
                cfg["earthquakes"].get("min_magnitude", 6.0),
                cfg["earthquakes"].get("max_age_hours", 6),
            )
        )

    if cfg.get("outdoor", {}).get("enabled"):
        signals.extend(
            outdoor.outdoor_signals(
                cfg["outdoor"].get("locations", []),
                cfg["outdoor"].get("uv_threshold", 11),
                cfg["outdoor"].get("dust_threshold", 500),
            )
        )

    return signals


def main() -> None:
    cfg = load_config()
    state = State()
    poster = Poster()

    ttl = cfg["dedup_ttl_hours"]
    max_run = cfg["limits"]["max_posts_per_run"]
    max_day = cfg["limits"]["max_posts_per_day"]
    max_month = cfg["limits"].get("max_posts_per_month", 500)

    candidates = collect(cfg)

    # Rank: most severe first.
    candidates.sort(key=lambda s: s.severity, reverse=True)

    posted = 0
    for sig in candidates:
        if posted >= max_run:
            break
        if state.posts_this_month() >= max_month:
            print("monthly post budget reached; stopping (cost cap).")
            break
        if state.posts_today() >= max_day:
            print("daily post budget reached; stopping.")
            break
        if state.already_posted(sig.dedup_key, ttl):
            continue

        text = render(sig)
        if poster.post(text):
            state.mark_posted(sig.dedup_key)
            state.increment_today()
            posted += 1

    if posted == 0:
        print("no new signals to post.")

    # Don't let local dry runs pollute the real dedup/budget state.
    if not poster.dry_run:
        state.prune(ttl)
        state.save()


if __name__ == "__main__":
    main()
