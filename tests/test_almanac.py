"""Almanac source: solar geometry, seasonal direction, and post wording."""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.sources import almanac


def _daily_now(dur_today=59460.0, dur_next=59340.0, zone="Europe/Amsterdam"):
    """Fake Open-Meteo daily data anchored to *now*, so the sunrise-relative
    window fires deterministically whenever the test runs. Sunrise is 10 min ago
    (inside the post-sunrise window); sunset is ~8 h out (outside its window)."""
    now = datetime.now(ZoneInfo(zone))
    sr = now - timedelta(minutes=10)
    ss = now + timedelta(hours=8)
    fmt = lambda d: d.strftime("%Y-%m-%dT%H:%M")
    return {
        "sunrise": [fmt(sr), fmt(sr + timedelta(days=1))],
        "sunset": [fmt(ss), fmt(ss + timedelta(days=1))],
        "daylight_duration": [dur_today, dur_next],
    }


# --- solar geometry ------------------------------------------------------
def test_sunrise_azimuth_due_east_at_equinox():
    # Declination 0 (equinox): the sun rises due east (090°) from any latitude.
    assert round(almanac._sunrise_azimuth(51.92, 0.0)) == 90


def test_sunrise_azimuth_swings_northeast_in_summer():
    # Positive declination (northern summer): sunrise is north of due east (<90°).
    assert almanac._sunrise_azimuth(51.92, 23.0) < 90


def test_solar_declination_seasonal_range():
    from datetime import date
    assert almanac._solar_declination(date(2026, 6, 21)) > 23     # near +23.4 at solstice
    assert almanac._solar_declination(date(2026, 12, 21)) < -23   # near -23.4


def test_delta_magnitude_words():
    assert almanac._delta_magnitude(-2.0) == "2 minutes"
    assert almanac._delta_magnitude(1.0) == "1 minute"
    assert almanac._delta_magnitude(0.5) == "30 seconds"


# --- almanac_data: symmetry + midpoint -----------------------------------
_DAILY = {
    "sunrise": ["2026-07-06T05:31", "2026-07-07T05:32"],
    "sunset": ["2026-07-06T22:02", "2026-07-07T22:01"],
    "daylight_duration": [59460.0, 59340.0],   # today longer -> losing 2 min/day
}


def test_almanac_data_bearings_are_symmetric(monkeypatch):
    monkeypatch.setattr(almanac, "_fetch", lambda lat, lon, zone: _DAILY)
    d = almanac.almanac_data(51.92, 4.48, "Europe/Amsterdam")
    assert d["sunset_az"] == 360 - d["sunrise_az"]        # mirror about N–S
    assert d["solar_noon"].strftime("%H:%M") == "13:46"   # midpoint of sun times
    assert d["delta_min"] < 0                             # losing daylight


# --- almanac_signals: wording, dynamic angle, seasonal direction ---------
_CFG = {"lat": 51.92, "lon": 4.48, "tz": "Europe/Amsterdam"}


def test_sunrise_post_uses_dynamic_angle(monkeypatch):
    monkeypatch.setattr(almanac, "_fetch", lambda lat, lon, zone: _daily_now())
    sigs = {s.dedup_key.split(":")[1]: s for s in almanac.almanac_signals(_CFG)}
    sr = sigs["sunrise"].text
    assert re.search(r"Sunrise bears \d{3}°", sr)         # 3-digit true bearing
    assert "true north sits" in sr and "off your left" in sr
    assert "90°" not in sr                                # not the fixed equinox value


def test_daylight_post_losing_season(monkeypatch):
    monkeypatch.setattr(almanac, "_fetch", lambda lat, lon, zone: _daily_now())
    sigs = {s.dedup_key.split(":")[1]: s for s in almanac.almanac_signals(_CFG)}
    assert "clawing off about 2 minutes" in sigs["daylight"].text


def test_daylight_post_gaining_season(monkeypatch):
    monkeypatch.setattr(almanac, "_fetch",
                        lambda lat, lon, zone: _daily_now(dur_today=59340.0, dur_next=59460.0))
    sigs = {s.dedup_key.split(":")[1]: s for s in almanac.almanac_signals(_CFG)}
    assert "clawing back about 2 minutes" in sigs["daylight"].text


def test_almanac_posts_are_low_priority_and_plain(monkeypatch):
    monkeypatch.setattr(almanac, "_fetch", lambda lat, lon, zone: _daily_now())
    posts = almanac.almanac_signals(_CFG)
    assert posts                                          # sunrise window is active
    for s in posts:
        assert s.category == "almanac"
        assert s.severity < 50            # never jumps a real weather/space alert
        assert not s.text.startswith("Heads up")   # no advisory softening
