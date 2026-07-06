"""Pure (non-network) helpers in the source modules."""
from src.sources import wording, nga, marine, outdoor, usgs, rotterdam


# --- outdoor._geo: "REGION, city" tag so it matches the weather sources ----
def test_outdoor_geo_tag_region_and_city():
    assert outdoor._geo("Miami", 25.76, -80.19) == "USA, Miami"
    assert outdoor._geo("Rome", 41.90, 12.50) == "EU, Rome"
    assert outdoor._geo("Riyadh", 24.71, 46.68) == "GCC, Riyadh"


# --- usgs._geo_tag: lift the state/country out of the epicenter string -----
def test_quake_geo_tag_lifts_us_state():
    assert usgs._geo_tag("92 km SW of Eureka, CA", 40.8, -124.16) == ("USA, California", "92 km SW of Eureka")


def test_quake_geo_tag_country_for_international():
    assert usgs._geo_tag("15 km E of Heraklion, Greece", 35.3, 25.2) == ("EU, Greece", "15 km E of Heraklion")


def test_quake_geo_tag_falls_back_to_region_only():
    # No trailing state/country -> region-only tag, place kept whole.
    assert usgs._geo_tag("Northern California", 39.5, -121.0) == ("USA", "Northern California")


# --- wording.tier -------------------------------------------------------
def test_tier_critical_event():
    assert wording.tier("Tornado Warning") == "critical"


def test_tier_flash_flood_is_not_critical():
    """Flash Flood is deliberately not critical so it can't dominate the feed —
    guard against it sneaking back in."""
    assert wording.tier("Flash Flood Warning") == "serious"


def test_tier_advisory_suffix():
    assert wording.tier("Heat Advisory") == "advisory"


# --- wording.topic ------------------------------------------------------
def test_topic_mapping():
    assert wording.topic("Flash Flood Warning") == "flood"
    assert wording.topic("Tornado Warning") == "tornado"
    assert wording.topic("Extreme Heat Warning") == "heat"
    assert wording.topic("Winter Storm Warning") == "winter"
    assert wording.topic("Dense Fog Warning") == "fog"
    # Marine warnings map via the sea/wind keywords.
    assert wording.topic("Gale Warning") == "marine"
    assert wording.topic("High Surf Warning") == "marine"


# --- wording.EVENT_FLOOR sanity (the pure-severity safety net) -----------
def test_event_floor_keeps_lifethreat_high():
    for ev in ("Tornado Warning", "Hurricane Warning", "Storm Surge Warning"):
        assert wording.EVENT_FLOOR[ev] >= 95
    assert wording.EVENT_FLOOR["Gale Warning"] == 74
    assert wording.EVENT_FLOOR["Hurricane Force Wind Warning"] == 95


def test_severity_for_falls_back_to_severe():
    # An event with no explicit floor ranks at the Severe default.
    assert wording.severity_for("Freeze Warning") == wording.SEVERITY_WEIGHT["Severe"]
    assert wording.severity_for("Tornado Warning") == 96


# --- rotterdam: derived alerts reuse the shared wording -------------------
def _fake_forecast(rotterdam_mod, current, daily):
    rotterdam_mod._forecast = lambda lat, lon, zone: {"current": current, "daily": daily}


_ROT_CFG = {"lat": 51.92, "lon": 4.48, "tz": "Europe/Amsterdam"}


def test_rotterdam_thunderstorm_reuses_wording():
    _fake_forecast(rotterdam, {"weather_code": 95}, {})
    sigs = rotterdam.rotterdam_signals(_ROT_CFG)
    assert len(sigs) == 1
    s = sigs[0]
    assert s.category == "rotterdam"
    assert s.topic == "thunderstorm"
    assert s.country == ""                     # whole account is Rotterdam; no geo tag
    assert s.text == ("A severe thunderstorm warning is active. "
                      + wording.ACTIONS["Severe Thunderstorm Warning"][0])


def test_rotterdam_heat_adds_degree_clause():
    _fake_forecast(rotterdam, {"weather_code": 1}, {"temperature_2m_max": [34], "temperature_2m_min": [20]})
    sigs = rotterdam.rotterdam_signals(_ROT_CFG)
    heat = [s for s in sigs if s.topic == "heat"]
    assert heat and "Highs near 34°C." in heat[0].text


def test_rotterdam_freeze_vs_extreme_cold():
    _fake_forecast(rotterdam, {"weather_code": 1}, {"temperature_2m_max": [3], "temperature_2m_min": [-15]})
    topics = {s.dedup_key.split(":")[1] for s in rotterdam.rotterdam_signals(_ROT_CFG)}
    assert "extremecold" in topics and "freeze" not in topics  # -15 is the severe tier only


def test_rotterdam_calm_is_silent():
    _fake_forecast(rotterdam, {"weather_code": 1, "wind_gusts_10m": 5, "precipitation": 0, "visibility": 9000},
                   {"temperature_2m_max": [18], "temperature_2m_min": [9]})
    assert rotterdam.rotterdam_signals(_ROT_CFG) == []


# --- nga._classify / _titlecase ------------------------------------------
def test_nga_classify_buckets():
    assert nga._classify("GPS JAMMING reported in the area") == "gps"
    assert nga._classify("MINE DANGER AREA established") == "mine"
    assert nga._classify("nothing relevant here") is None


def test_nga_titlecase_keeps_small_words_lower():
    assert nga._titlecase("BLACK SEA") == "Black Sea"
    assert nga._titlecase("GULF OF OMAN") == "Gulf of Oman"


# --- nga._region: keep the water body, drop the bordering country --------
def test_region_drops_bordering_country():
    assert nga._region("BLACK SEA\nROMANIA\nMines reported.", "4") == "the Black Sea"
    assert nga._region("NORTH PACIFIC\nHAWAII\nLaunch hazard.", "12") == "the North Pacific"


def test_region_keeps_multiple_water_areas():
    assert nga._region("BALTIC SEA\nGULF OF FINLAND\nFiring.", "A") == "the Baltic Sea, Gulf of Finland"


def test_region_falls_back_to_navarea_when_no_header():
    assert nga._region("123456Z JUN 26\nposition update", "4") == "the Western North Atlantic"


# --- marine wave / wind categories + their weights -----------------------
def test_marine_sea_categories_ordered():
    assert marine._category(5.0) == ("High", 74)
    assert marine._category(7.0) == ("Very high", 86)
    assert marine._category(10.0) == ("Phenomenal", 95)


def test_marine_wind_categories_ordered():
    assert marine._wind_category(40)[1] == 74    # Gale-force
    assert marine._wind_category(50)[1] == 86    # Storm-force
    assert marine._wind_category(70)[1] == 95    # Hurricane-force
