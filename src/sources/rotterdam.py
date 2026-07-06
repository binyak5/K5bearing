"""Rotterdam severe-weather alerts, derived from Open-Meteo (keyless).

The account is single-city now, so this is the one alert source. It reads
current conditions and today's forecast for Rotterdam and fires a warning when
a hazard threshold is crossed — thunderstorms, high wind, heavy rain/flooding,
dense fog, snow, ice, extreme heat, and freeze/extreme cold.

The phrasing is reused verbatim from the shared library (sources.wording, the
old US/EU/Gulf wording), so a Rotterdam alert reads exactly like the alerts the
account used to post. Each hazard maps to the NWS event whose guidance fits it.
Temperatures in °C, wind in km/h, visibility in metres. Fires at most once per
hazard per day (deduped on hazard + local date).
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

from ..config import USER_AGENT
from . import Signal, pick
from . import wording

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 20

# WMO weather codes grouped by the hazard they signal.
THUNDER_CODES = {95, 96, 99}
SNOW_CODES = {71, 73, 75, 77, 85, 86}
FREEZING_CODES = {56, 57, 66, 67}   # freezing drizzle / freezing rain
FOG_CODES = {45, 48}


def _forecast(lat: float, lon: float, zone: str) -> dict | None:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,wind_speed_10m,"
                   "wind_gusts_10m,visibility,weather_code,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": zone,
        "forecast_days": 1,
    }
    try:
        resp = requests.get(
            FORECAST_URL, headers={"User-Agent": USER_AGENT}, params=params, timeout=TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError):
        return None


def _emit(event: str, key: str, clause: str = "") -> Signal:
    """Build a Signal for one hazard, reusing the shared opener + guidance."""
    event_l = event.lower()
    article = "An" if event_l[:1] in "aeiou" else "A"
    # Single city, so no "for {area}" — Rotterdam rides in the timestamp prefix.
    opener = pick(wording.OPENERS, key + ":o").format(article=article, event=event_l, where="")
    action = pick(wording.ACTIONS.get(event, []), key + ":a")
    text = f"{opener}{clause} {action}".strip()
    return Signal(
        category="rotterdam",
        severity=wording.severity_for(event),
        text=text,
        dedup_key=key,
        hashtags=[wording.TAGS.get(event, "#Weather"), "#Rotterdam"],
        tz=None,  # set by caller
        tier=wording.tier(event),
        topic=wording.topic(event),
        # No geo tag: the whole account is Rotterdam, so the header is just the
        # local time + zone ("18:00 CEST"), with no redundant "Rotterdam" label.
        country="",
    )


def rotterdam_signals(cfg: dict) -> list[Signal]:
    lat, lon = cfg.get("lat"), cfg.get("lon")
    zone = cfg.get("tz", "Europe/Amsterdam")
    if lat is None or lon is None:
        return []

    data = _forecast(lat, lon, zone)
    if not data:
        return []
    cur = data.get("current") or {}
    daily = data.get("daily") or {}

    try:
        today = datetime.now(ZoneInfo(zone)).date().isoformat()
    except Exception:
        today = datetime.now(timezone.utc).date().isoformat()

    def key(tag: str) -> str:
        return f"rotterdam:{tag}:{today}"

    signals: list[Signal] = []

    def add(event: str, tag: str, clause: str = "") -> None:
        sig = _emit(event, key(tag), clause)
        sig.tz = zone
        signals.append(sig)

    # --- Sky-condition hazards (WMO weather code) ---
    code = cur.get("weather_code")
    code = int(code) if code is not None else None
    if code in THUNDER_CODES:
        add("Severe Thunderstorm Warning", "thunder")
    elif code in SNOW_CODES:
        add("Winter Storm Warning", "snow")
    elif code in FREEZING_CODES:
        add("Ice Storm Warning", "ice")

    # --- Dense fog (visibility in metres, or fog weather codes) ---
    vis = cur.get("visibility")
    fog_m = cfg.get("fog_visibility_m", 200)
    if (vis is not None and vis < fog_m) or code in FOG_CODES:
        add("Dense Fog Warning", "fog")

    # --- High wind (gusts) ---
    gust = cur.get("wind_gusts_10m")
    if gust is not None and gust >= cfg.get("wind_gust_kmh", 75):
        add("High Wind Warning", "wind")

    # --- Heavy rain / flooding (mm in the current hour) ---
    rain = cur.get("precipitation")
    if rain is not None:
        if rain >= cfg.get("flash_flood_mm", 25):
            add("Flash Flood Warning", "flashflood")
        elif rain >= cfg.get("rain_mm", 10):
            add("Flood Warning", "flood")

    # --- Extreme heat (today's forecast high) ---
    highs = daily.get("temperature_2m_max") or []
    high = highs[0] if highs and highs[0] is not None else None
    if high is not None and high >= cfg.get("heat_c", 30):
        add("Extreme Heat Warning", "heat", clause=f" Highs near {round(high)}°C.")

    # --- Freeze / extreme cold (today's forecast low) ---
    lows = daily.get("temperature_2m_min") or []
    low = lows[0] if lows and lows[0] is not None else None
    if low is not None:
        if low <= cfg.get("severe_cold_c", -10):
            add("Extreme Cold Warning", "extremecold", clause=f" Lows near {round(low)}°C.")
        elif low <= cfg.get("freeze_c", 0):
            add("Freeze Warning", "freeze", clause=f" Lows near {round(low)}°C.")

    return signals
