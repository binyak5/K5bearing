"""K5Bearing entrypoint.

Each invocation:
  1. Collects candidate signals from all enabled sources.
  2. Drops anything already posted (local dedup) or over the daily budget.
  3. Posts the most severe candidates, up to the per-run cap.

Run locally:   DRY_RUN=1 python -m src.main
On CI:         python -m src.main   (with X_* secrets in the environment)
"""
from __future__ import annotations

import os
import tempfile

from .config import load_config
from .validate import assert_valid
from .state import State
from .formatter import render, fingerprint
from .poster import Poster
from . import card
from .sources import swpc, gdacs, aurora, usgs, outdoor, nga, marine, hab, citywx, rotterdam, almanac, Signal


def collect(cfg: dict) -> list[Signal]:
    signals: list[Signal] = []

    # Scheduled Rotterdam update first: it's the one post that must not be missed,
    # so make its single Open-Meteo call before the run's heavy burst of calls
    # (marine/outdoor/gulf) that can briefly rate-limit the API.
    if cfg.get("city_weather", {}).get("enabled"):
        cw = cfg["city_weather"]
        signals.extend(
            citywx.city_signals(
                cw.get("locations", []),
                cw.get("morning_hours", [7, 12]),
                cw.get("evening_hours", [19, 24]),
            )
        )

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

    if cfg.get("solar_wind", {}).get("enabled"):
        sig = swpc.solar_wind_signal(cfg["solar_wind"].get("speed_threshold_kms", 600))
        if sig:
            signals.append(sig)

    if cfg.get("radiation", {}).get("enabled"):
        sig = swpc.radiation_signal(cfg["radiation"].get("min_scale", 1))
        if sig:
            signals.append(sig)

    if cfg.get("radio_blackout", {}).get("enabled"):
        sig = swpc.blackout_signal(cfg["radio_blackout"].get("min_scale", 1))
        if sig:
            signals.append(sig)

    if cfg.get("rotterdam", {}).get("enabled"):
        signals.extend(rotterdam.rotterdam_signals(cfg["rotterdam"]))

    if cfg.get("almanac", {}).get("enabled"):
        signals.extend(almanac.almanac_signals(cfg["almanac"]))

    if cfg.get("marine_seas", {}).get("enabled"):
        ms = cfg["marine_seas"]
        areas = ms.get("areas", [])
        signals.extend(marine.sea_signals(areas, ms.get("wave_height_threshold", 4.0)))
        signals.extend(marine.fog_signals(areas, ms.get("fog_visibility_m", 1000)))
        signals.extend(marine.wind_signals(areas, ms.get("wind_gale_kt", 34)))
        signals.extend(
            marine.swell_signals(areas, ms.get("swell_period_s", 13), ms.get("swell_height_m", 2.0))
        )

    if cfg.get("algal_blooms", {}).get("enabled"):
        ab = cfg["algal_blooms"]
        signals.extend(
            hab.hab_signals(
                ab.get("cell_threshold", 100000),
                ab.get("da_threshold", 1.0),
                ab.get("lookback_days", 14),
            )
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
        locations = cfg["outdoor"].get("locations", [])
        signals.extend(
            outdoor.outdoor_signals(
                locations,
                cfg["outdoor"].get("uv_threshold", 11),
                cfg["outdoor"].get("dust_threshold", 500),
            )
        )
        signals.extend(outdoor.lightning_signals(locations))

    return signals


def main() -> None:
    cfg = load_config()
    assert_valid(cfg)  # fail loudly on config drift before spending any API budget
    state = State()
    poster = Poster()

    ttl = cfg["dedup_ttl_hours"]
    max_run = cfg["limits"]["max_posts_per_run"]
    max_day = cfg["limits"]["max_posts_per_day"]
    max_month = cfg["limits"].get("max_posts_per_month", 500)
    cat_caps = cfg["limits"].get("category_daily_caps", {})  # {category: max/day}
    min_gap = cfg["limits"].get("min_minutes_between_posts", 0)
    area_cooldown = cfg["limits"].get("area_cooldown_hours", 2)  # one region per N hours
    media_enabled = cfg.get("media", {}).get("enabled", False)

    candidates = collect(cfg)

    # Ranking is by raw severity, highest first. No topic, source, or tier gets a
    # boost — severity alone decides priority. (The scheduled Rotterdam update
    # still sorts to the top simply because its severity is set to 1000.)
    candidates.sort(key=lambda s: s.severity, reverse=True)

    def topic_of(sig) -> str:
        return sig.topic or sig.category

    def eligible(sig, ignore_cap: bool = False) -> bool:
        if state.already_posted(sig.dedup_key, ttl):
            return False
        # Per-category daily cap: keep one noisy source (e.g. maritime on a busy
        # day) from eating the whole budget. Soft: when `ignore_cap` is set (the
        # overflow pass, used only if nothing else is eligible) it's relaxed, so
        # the feed doesn't go silent under the daily budget just because the only
        # active regions have hit their caps.
        if not ignore_cap:
            cap = cat_caps.get(sig.category)
            if cap is not None and state.posts_today_in(sig.category) >= cap:
                return False
        # Content backstop: suppress anything that renders to the same words as a
        # recent post even under a different dedup_key (cross-source dupes).
        if state.already_posted(fingerprint(sig), ttl):
            return False
        # Per-area cooldown: during an outbreak one state/country can issue many
        # distinct warnings; hold the same area back for a few hours so it doesn't
        # dominate the feed. A strictly more severe warning still breaks through.
        # Keyed on the geo tag (e.g. "USA, Illinois"); signals without one (space
        # weather, marine, quakes) carry no area and are unaffected.
        area = getattr(sig, "country", "")
        if area and state.area_blocked(area, sig.severity, area_cooldown):
            return False
        return True

    # The scheduled Rotterdam update is exempt from the budget caps: it's a
    # fixed, tiny number of posts a day and must never be dropped just because
    # routine alerts used up the daily budget earlier.
    def exempt(sig) -> bool:
        return sig.category == "cityweather"

    # Spacing: hold routine posts to at least min_gap minutes apart so the feed
    # is evenly paced and the daily budget lasts. The scheduled Rotterdam update
    # ignores this (it posts in its window regardless).
    gap_ok = state.minutes_since_last_post() >= min_gap

    posted = 0
    last_topic = state.last_topic()
    remaining = list(candidates)
    while posted < max_run:
        day_full = state.posts_today() >= max_day
        month_full = state.posts_this_month() >= max_month

        # Pick the most severe eligible signal whose topic differs from the last
        # post. This no-repeat-in-a-row rule applies uniformly to every topic —
        # nothing is exempt — so a same-topic signal is only used as a fallback
        # when nothing else is available this run. Non-exempt posts must clear
        # the budget and the minimum spacing gap; the scheduled Rotterdam update
        # is exempt from both.
        def best(ignore_cap: bool):
            choice = fallback = None
            for sig in remaining:
                if not exempt(sig) and (day_full or month_full or not gap_ok):
                    continue
                if not eligible(sig, ignore_cap):
                    continue
                if topic_of(sig) == last_topic:
                    fallback = fallback or sig
                    continue
                return sig
            return fallback

        # Normal pass respects the per-category caps; only if that finds nothing
        # do we allow a capped category to overflow (still within the daily budget).
        choice = best(False) or best(True)
        if choice is None:
            if day_full:
                print("daily post budget reached (only scheduled posts allowed).")
            break

        # Attach a media card to signals that carry card data (the per-event
        # selection lives in the sources: only chosen event types set `card`).
        image_path = None
        if media_enabled and getattr(choice, "card", None):
            try:
                fd, image_path = tempfile.mkstemp(suffix=".png", prefix="k5card_")
                os.close(fd)
                if card.card_png_for(choice, image_path) is None:
                    image_path = None
            except Exception as exc:  # rendering must never block the post
                print(f"card render failed: {exc}")
                image_path = None

        if poster.post(render(choice), image_path):
            state.mark_posted(choice.dedup_key)
            state.mark_posted(fingerprint(choice))
            state.increment_today(choice.category)
            state.mark_post_time()
            area = getattr(choice, "country", "")
            if area:
                state.mark_area_post(area, choice.severity)
            last_topic = topic_of(choice)
            state.set_last_topic(last_topic)
            posted += 1
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        remaining.remove(choice)

    if posted == 0:
        print("no new signals to post.")

    # Don't let local dry runs pollute the real dedup/budget state.
    if not poster.dry_run:
        state.prune(ttl)
        state.save()


if __name__ == "__main__":
    main()
