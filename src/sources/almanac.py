"""Almanac posts for Rotterdam: sunrise/sunset compass bearings, solar noon
(true-south / shadow-north calibration), and the daylight ledger.

All derived from Open-Meteo's daily sun data plus a little solar geometry — no
API key, no extra dependency. These are scheduled daily-rhythm posts, not
threshold alerts: each fires once per day in its window and is deduped per day.

Bearings are true (geographic) bearings. The sunrise azimuth comes from the
observer's latitude and the sun's declination:
    cos(A) = sin(declination) / cos(latitude)     (A measured from true north)
which gives ~090° at the equinoxes, swinging north-east in summer and south-east
in winter. Sunset mirrors it about the north–south line (360 − A).
"""
from __future__ import annotations

import math
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import requests

from ..config import USER_AGENT
from . import Signal, pick

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 20

# ---- wording ------------------------------------------------------------
# {az} is a 3-digit true bearing (051, 309); {off} is the angle to true north.
SUNRISE_VARIANTS = [
    "Sunrise bears {az}° today. Line yourself up with it, and true north sits {off}° off your left.",
]
SUNSET_VARIANTS = [
    "Sun bears {az}° tonight. Line yourself up with it, and true north sits {off}° off your right.",
]
SOLAR_NOON_VARIANTS = [
    "Solar noon. The sun is locked due true south right now. Your shadow locks straight true north — the day's cleanest compass check.",
]
# Two seasonal twins: the light is either growing (Dec–Jun) or shrinking (Jun–Dec).
DAYLIGHT_GAINING = [
    "Daylight today: {len}, and the sun's clawing back about {delta} a day now.",
]
DAYLIGHT_LOSING = [
    "Daylight today: {len}, and the light's clawing off about {delta} a day now.",
]


def _solar_declination(d: date) -> float:
    """Sun's declination (degrees) for a date — a compact seasonal approximation."""
    n = d.timetuple().tm_yday
    return -23.44 * math.cos(math.radians(360.0 / 365.0 * (n + 10)))


def _sunrise_azimuth(lat: float, decl: float) -> float:
    """Sunrise azimuth in degrees from true north (sunset = 360 − this)."""
    x = math.sin(math.radians(decl)) / math.cos(math.radians(lat))
    x = max(-1.0, min(1.0, x))
    return math.degrees(math.acos(x))


def _fmt_hm(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int(round((seconds % 3600) / 60))
    return f"{h}h {m:02d}m"


def _fetch(lat: float, lon: float, zone: str) -> dict | None:
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "sunrise,sunset,daylight_duration",
        "timezone": zone,
        "forecast_days": 2,
    }
    try:
        resp = requests.get(FORECAST_URL, headers={"User-Agent": USER_AGENT},
                            params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("daily") or None
    except (requests.RequestException, ValueError):
        return None


def almanac_data(lat: float, lon: float, zone: str) -> dict | None:
    """Today's sun figures for Rotterdam: sunrise/sunset times + bearings, solar
    noon, daylight length, and the day-over-day change. None on any failure."""
    daily = _fetch(lat, lon, zone)
    if not daily:
        return None
    try:
        sunrise = datetime.fromisoformat(daily["sunrise"][0])
        sunset = datetime.fromisoformat(daily["sunset"][0])
        dur_today = float(daily["daylight_duration"][0])
        dur_next = float(daily["daylight_duration"][1])
    except (KeyError, IndexError, TypeError, ValueError):
        return None

    decl = _solar_declination(sunrise.date())
    sr_az = _sunrise_azimuth(lat, decl)
    solar_noon = sunrise + (sunset - sunrise) / 2
    delta_min = (dur_next - dur_today) / 60.0

    return {
        "sunrise": sunrise,
        "sunset": sunset,
        "sunrise_az": round(sr_az),
        "sunset_az": round(360 - sr_az),
        "solar_noon": solar_noon,
        "daylight": _fmt_hm(dur_today),
        "delta_min": delta_min,               # +gaining / −losing, minutes/day
    }


def _delta_magnitude(delta_min: float) -> str:
    """The size of the day-over-day daylight change as words ('2 minutes' /
    '45 seconds'); direction is carried by which template is chosen."""
    mag = abs(delta_min)
    if mag < 1:
        n = int(round(mag * 60))
        return f"{n} second" + ("s" if n != 1 else "")
    n = int(round(mag))
    return f"{n} minute" + ("s" if n != 1 else "")


def almanac_signals(cfg: dict) -> list[Signal]:
    lat, lon = cfg.get("lat"), cfg.get("lon")
    zone = cfg.get("tz", "Europe/Amsterdam")
    if lat is None or lon is None:
        return []
    try:
        now = datetime.now(ZoneInfo(zone))
    except Exception:
        return []

    # All timing is relative to the day's actual sun events, so the posts stay
    # correct year-round as sunrise/sunset swing across the seasons.
    sunrise_win = cfg.get("sunrise_window_min", 180)   # post within N min AFTER sunrise
    sunset_win = cfg.get("sunset_window_min", 120)     # post within N min BEFORE sunset
    noon_slack = cfg.get("solar_noon_slack_min", 15)   # post within N min of solar noon

    data = almanac_data(lat, lon, zone)
    if not data:
        return []
    today = now.date().isoformat()
    tzinfo = now.tzinfo
    sunrise = data["sunrise"].replace(tzinfo=tzinfo)
    sunset = data["sunset"].replace(tzinfo=tzinfo)
    noon = data["solar_noon"].replace(tzinfo=tzinfo)

    def sig(tag: str, text: str, topic: str) -> Signal:
        return Signal(
            category="almanac",
            severity=40,            # low: a quiet-day rhythm post, never jumps a real alert
            text=text,
            dedup_key=f"almanac:{tag}:{today}",
            hashtags=["#Compass", "#Rotterdam"],
            tz=zone,
            # Not "advisory": these are almanac notes, not safety warnings, so they
            # post as written (no softening "Heads up," lead).
            tier="serious",
            topic=topic,
        )

    # Facing the sunrise, true north is (sunrise azimuth)° to your left; facing
    # the sunset it's the same angle to your right (the two are symmetric about
    # the north–south line). So one offset serves both lines.
    off = data["sunrise_az"]
    out: list[Signal] = []

    # Sunrise bearing + daylight ledger — the hours just after sunrise.
    if 0 <= (now - sunrise).total_seconds() <= sunrise_win * 60:
        out.append(sig("sunrise", pick(SUNRISE_VARIANTS, f"sunrise:{today}").format(
            az=f"{data['sunrise_az']:03d}", off=off), "sunrise"))
        gaining = data["delta_min"] >= 0
        tmpl = DAYLIGHT_GAINING if gaining else DAYLIGHT_LOSING
        out.append(sig("daylight", pick(tmpl, f"daylight:{today}").format(
            len=data["daylight"], delta=_delta_magnitude(data["delta_min"])), "daylight"))

    # Solar noon — within a few minutes of the sun crossing due south.
    if abs((now - noon).total_seconds()) <= noon_slack * 60:
        out.append(sig("solarnoon", pick(SOLAR_NOON_VARIANTS, f"noon:{today}"), "solarnoon"))

    # Sunset bearing — the run-up to sunset.
    if 0 <= (sunset - now).total_seconds() <= sunset_win * 60:
        out.append(sig("sunset", pick(SUNSET_VARIANTS, f"sunset:{today}").format(
            az=f"{data['sunset_az']:03d}", off=off), "sunset"))

    return out
