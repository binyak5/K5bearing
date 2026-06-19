"""Config validator: clean on the shipped config, and bites on each drift class."""
import copy

from src.config import load_config
from src.validate import validate_config


def test_shipped_config_is_clean():
    """The real config.yaml must pass with zero errors and zero warnings —
    this is the regression guard for all our hand-edits."""
    errors, warnings = validate_config(load_config())
    assert errors == [], errors
    assert warnings == [], warnings


def test_event_without_wording_errors():
    cfg = copy.deepcopy(load_config())
    cfg["weather"]["events"].append("Made Up Warning")
    errors, _ = validate_config(cfg)
    assert any("Made Up Warning" in e for e in errors)


def test_small_craft_advisory_is_exempt():
    """SCA only posts via the roundup, so it's allowed in events with no ACTIONS."""
    cfg = copy.deepcopy(load_config())
    assert "Small Craft Advisory" in cfg["weather"]["events"]
    errors, _ = validate_config(cfg)
    assert not any("Small Craft Advisory" in e for e in errors)


def test_unknown_eu_country_errors():
    cfg = copy.deepcopy(load_config())
    cfg["weather_eu"]["countries"].append("kazakhstan")
    errors, _ = validate_config(cfg)
    assert any("kazakhstan" in e and "timezone" in e for e in errors)
    assert any("kazakhstan" in e and "ISO code" in e for e in errors)


def test_unknown_cap_category_errors():
    cfg = copy.deepcopy(load_config())
    cfg["limits"]["category_daily_caps"]["nonsense"] = 5
    errors, _ = validate_config(cfg)
    assert any("nonsense" in e for e in errors)


def test_location_missing_coords_errors():
    cfg = copy.deepcopy(load_config())
    cfg["gulf_weather"]["locations"].append({"name": "Nowhere", "tz": "Asia/Dubai"})
    errors, _ = validate_config(cfg)
    assert any("Nowhere" in e and "lat/lon" in e for e in errors)


def test_gulf_tz_without_code_warns_not_errors():
    cfg = copy.deepcopy(load_config())
    cfg["gulf_weather"]["locations"].append(
        {"name": "Odd City", "lat": 1.0, "lon": 2.0, "tz": "Antarctica/Troll"}
    )
    errors, warnings = validate_config(cfg)
    assert not any("Odd City" in e for e in errors)
    assert any("Odd City" in w for w in warnings)
