"""NOAA Space Weather Prediction Center (SWPC) — solar storms, solar flares,
geomagnetic activity, and the compass-accuracy signal derived from the Kp index.

All endpoints are public, free, and require no API key.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from ..config import USER_AGENT
from . import Signal, pick

KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
ALERTS_URL = "https://services.swpc.noaa.gov/products/alerts.json"
FLARES_URL = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-latest.json"
SCALES_URL = "https://services.swpc.noaa.gov/products/noaa-scales.json"
PLASMA_URL = "https://services.swpc.noaa.gov/products/solar-wind/plasma-2-hour.json"

# NOAA S-scale (solar radiation storm) level -> label.
S_LABEL = {1: "minor", 2: "moderate", 3: "strong", 4: "severe", 5: "extreme"}
# NOAA R-scale (HF radio blackout) level -> label.
R_LABEL = {1: "minor", 2: "moderate", 3: "strong", 4: "severe", 5: "extreme"}

TIMEOUT = 20

# Kp -> NOAA G-scale geomagnetic storm level.
G_SCALE = {5: "G1", 6: "G2", 7: "G3", 8: "G4", 9: "G5"}

# Solar flare class letter -> rank, for thresholding.
FLARE_RANK = {"A": 0, "B": 1, "C": 2, "M": 3, "X": 4}


def _get_json(url: str):
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def current_kp() -> float | None:
    """Most recent planetary K-index value (0-9).

    Feed is a list of dicts: {"time_tag", "Kp", "a_running", "station_count"}.
    """
    try:
        rows = _get_json(KP_URL)
    except (requests.RequestException, ValueError):
        return None
    if not rows:
        return None
    try:
        return float(rows[-1]["Kp"])
    except (ValueError, KeyError, TypeError, IndexError):
        return None


def geomagnetic_signal(kp_threshold: int) -> Signal | None:
    kp = current_kp()
    if kp is None or kp < kp_threshold:
        return None
    level = G_SCALE.get(int(kp), "G1")
    key = f"geomag:{level}"
    if kp < 7:
        variants = [
            f"A {level} geomagnetic storm is underway at Kp {kp:.0f}, and magnetic "
            "north is drifting, so a compass can read a few degrees off true. "
            "Check any bearing against GPS or a known landmark before you rely on it.",
            f"A {level} geomagnetic storm has set in at Kp {kp:.0f}, pulling magnetic "
            "north off true, so a compass may be a few degrees out. Confirm any "
            "bearing with GPS or a fixed landmark before trusting it.",
        ]
    else:
        variants = [
            f"A {level} geomagnetic storm has ramped up to Kp {kp:.0f}, throwing magnetic "
            "north off by several degrees, so trust GPS or a celestial bearing and treat "
            "the compass as a rough guide until it settles.",
        ]
    # Dedup per storm level (within the dedup TTL) so escalations re-post but a
    # steady state doesn't.
    # G1(kp5)=64 ... G5(kp9)=88: space weather sits in the upper-"serious" band,
    # on-theme for a compass brand but below the life-threatening weather tier.
    return Signal(
        category="geomagnetic",
        severity=34 + int(kp) * 6,
        text=pick(variants, key),
        dedup_key=key,
        hashtags=["#SpaceWeather", "#Compass"],
    )


def solar_wind_signal(speed_threshold: float = 600) -> Signal | None:
    """High-speed solar wind stream from the NOAA real-time plasma feed
    (DSCOVR/ACE). A fast stream stirs the magnetic field — on brand for the
    compass/bearing angle. Fires once per day when speed crosses the threshold.
    """
    try:
        rows = _get_json(PLASMA_URL)
    except (requests.RequestException, ValueError):
        return None
    if not rows or len(rows) < 2:
        return None
    # rows[0] is the header ["time_tag","density","speed","temperature"];
    # scan from the newest end for the latest valid speed reading.
    speed = None
    for row in reversed(rows[1:]):
        try:
            speed = float(row[2])
            break
        except (TypeError, ValueError, IndexError):
            continue
    if speed is None or speed < speed_threshold:
        return None
    spd = round(speed)
    key = f"solarwind:{datetime.now(timezone.utc).date().isoformat()}"
    text = (
        f"The solar wind is screaming past Earth at {spd} km/s, a high-speed stream "
        "raking the magnetic field. Expect the compass needle to grow restless and "
        "the aurora to push toward lower latitudes."
    )
    return Signal(
        category="solarwind",
        severity=70,
        text=text,
        dedup_key=key,
        hashtags=["#SpaceWeather", "#SolarWind"],
    )


def _parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def flare_signal(min_class: str = "M", max_age_hours: int = 6) -> Signal | None:
    """Most recent significant solar flare from the GOES X-ray sensor."""
    min_rank = FLARE_RANK.get(min_class.upper(), 3)
    try:
        rows = _get_json(FLARES_URL)
    except (requests.RequestException, ValueError):
        return None
    if not rows:
        return None
    flare = rows[0]
    mclass = (flare.get("max_class") or "").strip()
    if not mclass or FLARE_RANK.get(mclass[0].upper(), -1) < min_rank:
        return None

    peaked = _parse_utc(flare.get("max_time", ""))
    if peaked is None:
        return None
    if datetime.now(timezone.utc) - peaked > timedelta(hours=max_age_hours):
        return None

    letter = mclass[0].upper()
    if letter == "X":
        impact = (
            "Flares this strong can trigger widespread shortwave radio blackouts "
            "on the daylit side of Earth and impair GPS and HF communications."
        )
    else:  # M class
        impact = (
            "Flares this strong can cause brief HF (shortwave) radio blackouts on "
            "the daylit side of Earth."
        )
    hhmm = peaked.strftime("%H:%M")
    article = "An" if letter in ("A", "M", "X") else "A"  # letter-name sound
    key = f"flare:{flare.get('max_time')}"
    leads = [
        f"The Sun fired off {article.lower()} {mclass} flare, peaking at {hhmm} UTC.",
    ]
    text = f"{pick(leads, key + ':l')} {impact}"
    return Signal(
        category="flare",
        severity=80 if letter == "X" else 62,
        text=text,
        dedup_key=key,
        hashtags=["#SolarFlare", "#SpaceWeather"],
    )


def radiation_signal(min_scale: int = 1) -> Signal | None:
    """Current solar radiation storm from the NOAA S-scale."""
    try:
        data = _get_json(SCALES_URL)
    except (requests.RequestException, ValueError):
        return None
    raw = ((data or {}).get("0", {}).get("S") or {}).get("Scale")
    try:
        level = int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        return None
    if level < min_scale:
        return None
    label = S_LABEL.get(level, "minor")
    key = f"radiation:S{level}"
    variants = [
        f"A solar radiation storm has reached S{level} ({label}). Polar flights can lose HF radio and satellite navigation may degrade.",
        f"Solar radiation has surged to an S{level} ({label}) storm. Expect HF blackouts over the poles and possible satellite navigation glitches.",
    ]
    return Signal(
        category="radiation",
        severity=64 + level * 4,
        text=pick(variants, key),
        dedup_key=key,
        hashtags=["#SolarRadiation", "#SpaceWeather"],
    )


def blackout_signal(min_scale: int = 1) -> Signal | None:
    """Current HF radio blackout from the NOAA R-scale."""
    try:
        data = _get_json(SCALES_URL)
    except (requests.RequestException, ValueError):
        return None
    raw = ((data or {}).get("0", {}).get("R") or {}).get("Scale")
    try:
        level = int(raw) if raw is not None else 0
    except (TypeError, ValueError):
        return None
    if level < min_scale:
        return None
    label = R_LABEL.get(level, "minor")
    key = f"blackout:R{level}"
    variants = [
        f"A radio blackout has surged to R{level} ({label}), the Sun jamming high-frequency radio across the daylit side of Earth. Mariners and aviators leaning on HF should expect dropouts and dead air until it fades.",
        f"Solar flaring has driven an R{level} ({label}) radio blackout, smothering high-frequency radio on the sunlit face of the planet. Expect HF comms to wash out and navigation signals to wander until it clears.",
    ]
    return Signal(
        category="blackout",
        severity=62 + level * 4,
        text=pick(variants, key),
        dedup_key=key,
        hashtags=["#RadioBlackout", "#SpaceWeather"],
    )


def _alert_headline(message: str) -> str:
    """Pull the human 'ALERT:'/'WARNING:'/'SUMMARY:' line out of an SWPC message."""
    for line in message.splitlines():
        s = line.strip()
        for tag in ("ALERT:", "WARNING:", "SUMMARY:", "WATCH:"):
            if s.startswith(tag):
                return s[len(tag):].strip()
    return ""


def _parse_issue(s: str) -> datetime | None:
    """SWPC issue_datetime like '2026-06-17 14:20:00.000' (UTC, no tz)."""
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s.strip(), fmt).replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            continue
    return None


def solar_signals(watch_prefixes: list[str], max_age_hours: int = 24) -> list[Signal]:
    try:
        rows = _get_json(ALERTS_URL)
    except (requests.RequestException, ValueError):
        return []

    now = datetime.now(timezone.utc)
    signals: list[Signal] = []
    # Newest first; only consider the most recent handful.
    for entry in rows[:25]:
        pid = (entry.get("product_id") or "").strip()
        if not any(pid.startswith(p) for p in watch_prefixes):
            continue
        message = entry.get("message", "")
        headline = _alert_headline(message)
        if not headline:
            continue
        issued = (entry.get("issue_datetime") or "").strip()
        # Freshness: skip alerts issued more than max_age_hours ago.
        issued_dt = _parse_issue(issued)
        if issued_dt is not None and (now - issued_dt) > timedelta(hours=max_age_hours):
            continue
        text = f"Space weather alert: {headline[:210]}"
        signals.append(
            Signal(
                category="solar",
                severity=62,
                text=text,
                dedup_key=f"solar:{pid}:{issued}",
                hashtags=["#SpaceWeather", "#SolarStorm"],
            )
        )
    return signals
