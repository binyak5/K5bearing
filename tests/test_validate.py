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


def test_unknown_cap_category_errors():
    cfg = copy.deepcopy(load_config())
    cfg["limits"]["category_daily_caps"]["nonsense"] = 5
    errors, _ = validate_config(cfg)
    assert any("nonsense" in e for e in errors)


def test_city_weather_location_missing_coords_errors():
    cfg = copy.deepcopy(load_config())
    cfg["city_weather"]["locations"].append({"name": "Nowhere", "tz": "Europe/Amsterdam"})
    errors, _ = validate_config(cfg)
    assert any("Nowhere" in e and "lat/lon" in e for e in errors)


def test_rotterdam_missing_coords_errors():
    cfg = copy.deepcopy(load_config())
    cfg["rotterdam"].pop("lat")
    errors, _ = validate_config(cfg)
    assert any("rotterdam" in e and "lat/lon" in e for e in errors)


def test_rotterdam_missing_tz_errors():
    cfg = copy.deepcopy(load_config())
    cfg["rotterdam"]["tz"] = ""
    errors, _ = validate_config(cfg)
    assert any("rotterdam" in e and "tz" in e for e in errors)
