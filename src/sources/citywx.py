"""Routine twice-daily city weather updates (not alerts), from Open-Meteo's
keyless forecast API. Posts a morning and an evening outlook for each watched
city, in the city's local time and degrees Celsius.

Unlike the event feeds this fires on a schedule: during the morning window it
emits a "today" outlook, during the evening window a "tonight + tomorrow" one.
The posting loop's dedup (keyed per city/date/slot) keeps it to once per slot.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from ..config import USER_AGENT
from . import Signal, pick

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 20

# WMO weather code -> a clean noun phrase that reads after "with ...".
WX = {
    0: "clear skies", 1: "mainly clear skies", 2: "broken cloud", 3: "overcast skies",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "steady rain", 65: "heavy rain",
    66: "freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "rain showers", 81: "rain showers", 82: "heavy rain showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorms", 96: "thunderstorms with hail", 99: "thunderstorms with hail",
}

MORNING_VARIANTS = [
    "Rotterdam, good morning. It is {temp}°C with {cond}, on the way to a high of {high}°C and a low of {low}°C. Winds are {wdesc} near {wind} km/h.",
    "Morning over Rotterdam. {temp}°C to start with {cond}, the day reaching {high}°C and easing to {low}°C. Winds are {wdesc} near {wind} km/h.",
]

EVENING_VARIANTS = [
    "Rotterdam this evening, {temp}°C with {cond}. Overnight settles to {low}°C, and tomorrow climbs to {high}°C with {cond_tmr}.",
    "Evening over Rotterdam. {temp}°C with {cond} right now. Tonight dips to {low}°C, and tomorrow tops out at {high}°C with {cond_tmr}.",
]


def _describe(code) -> str:
    try:
        return WX.get(int(code), "changeable skies")
    except (TypeError, ValueError):
        return "changeable skies"


def _wind_desc(kmh: float) -> str:
    if kmh < 5:
        return "calm"
    if kmh < 20:
        return "light"
    if kmh < 39:
        return "moderate"
    if kmh < 62:
        return "strong"
    return "gale-force"


def _slot(now: datetime, morning: list, evening: list) -> str | None:
    """Which update window the local time falls in, if any."""
    h = now.hour
    if morning[0] <= h < morning[1]:
        return "morning"
    if evening[0] <= h < evening[1]:
        return "evening"
    return None


def _forecast(lat: float, lon: float, zone: str) -> dict | None:
    try:
        resp = requests.get(
            FORECAST_URL,
            headers={"User-Agent": USER_AGENT},
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,weather_code",
                "timezone": zone,
                "forecast_days": 2,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError):
        return None


def city_signals(locations: list[dict], morning: list, evening: list) -> list[Signal]:
    signals: list[Signal] = []
    for loc in locations:
        name, lat, lon = loc.get("name"), loc.get("lat"), loc.get("lon")
        zone = loc.get("tz", "UTC")
        if name is None or lat is None or lon is None:
            continue
        try:
            now = datetime.now(ZoneInfo(zone))
        except Exception:
            continue
        slot = _slot(now, morning, evening)
        if slot is None:
            continue

        data = _forecast(lat, lon, zone)
        if not data:
            continue
        cur = data.get("current", {})
        daily = data.get("daily", {})
        try:
            temp = round(cur["temperature_2m"])
            wind = round(cur.get("wind_speed_10m", 0))
            cond = _describe(cur.get("weather_code"))
            highs = daily["temperature_2m_max"]
            lows = daily["temperature_2m_min"]
            codes = daily["weather_code"]
        except (KeyError, TypeError, ValueError):
            continue

        key = f"citywx:{name.lower()}:{now.date().isoformat()}:{slot}"
        if slot == "morning":
            text = pick(MORNING_VARIANTS, key).format(
                temp=temp, cond=cond, high=round(highs[0]), low=round(lows[0]),
                wdesc=_wind_desc(wind), wind=wind,
            )
        else:  # evening: tonight's low + tomorrow's high/conditions
            text = pick(EVENING_VARIANTS, key).format(
                temp=temp, cond=cond, low=round(lows[1]), high=round(highs[1]),
                cond_tmr=_describe(codes[1]),
            )

        signals.append(
            Signal(
                category="cityweather",
                severity=65,   # reliably wins a slot, but genuine emergencies (>=85) still come first
                text=text,
                dedup_key=key,
                hashtags=["#Rotterdam", "#Weather"],
                tz=zone,
            )
        )
    return signals
