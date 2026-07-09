"""Tide source: high/low classification, next-high selection, lead-window post."""
from datetime import datetime, timezone, timedelta

from src.sources import tides


# --- high/low classification (extremes alternate) ------------------------
def test_high_water_flags_starting_high():
    assert tides._high_water_flags([110, -44, 93, -78]) == [True, False, True, False]


def test_high_water_flags_starting_low():
    assert tides._high_water_flags([-44, 110, -78, 93]) == [False, True, False, True]


# --- next_high_water + post, with the API mocked -------------------------
def _fake_extremes(minutes_to_high=30):
    now = datetime.now(timezone.utc)
    return [
        (now + timedelta(minutes=minutes_to_high), 110.0),   # high (1.1 m)
        (now + timedelta(hours=6), -40.0),                   # low
        (now + timedelta(hours=12), 100.0),                  # high
    ]


def test_next_high_water_converts_and_scales(monkeypatch):
    monkeypatch.setattr(tides, "_fetch_extremes", lambda code, hours=30: _fake_extremes())
    when, height_m = tides.next_high_water("hoekvanholland", "Europe/Amsterdam")
    assert height_m == 1.1                       # 110 cm -> 1.1 m
    assert when.tzinfo is not None               # localised, not naive


def test_tide_signal_fires_in_lead_window(monkeypatch):
    monkeypatch.setattr(tides, "_fetch_extremes", lambda code, hours=30: _fake_extremes(30))
    cfg = {"location_code": "hoekvanholland", "name": "Hoek van Holland",
           "tz": "Europe/Amsterdam", "lead_min": 90}
    sigs = tides.tide_signals(cfg)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.category == "tides" and s.severity < 50
    assert s.text.startswith("Next high water at Hoek van Holland: ")
    assert s.text.endswith(", 1.1 m.")


def test_tide_signal_silent_outside_lead(monkeypatch):
    # Next high water is 5 h away -> outside the 90-min lead window -> no post.
    monkeypatch.setattr(tides, "_fetch_extremes", lambda code, hours=30: _fake_extremes(300))
    cfg = {"location_code": "hoekvanholland", "tz": "Europe/Amsterdam", "lead_min": 90}
    assert tides.tide_signals(cfg) == []


def test_tide_signal_none_on_api_failure(monkeypatch):
    monkeypatch.setattr(tides, "_fetch_extremes", lambda code, hours=30: None)
    assert tides.tide_signals({"tz": "Europe/Amsterdam"}) == []
