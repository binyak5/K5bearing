"""Pure (non-network) helpers in the source modules."""
from src.sources import nws, meteoalarm, nga, marine, outdoor


# --- outdoor._geo: "REGION, city" tag so it matches the weather sources ----
def test_outdoor_geo_tag_region_and_city():
    assert outdoor._geo("Miami", 25.76, -80.19) == "USA, Miami"
    assert outdoor._geo("Rome", 41.90, 12.50) == "EU, Rome"
    assert outdoor._geo("Riyadh", 24.71, 46.68) == "GCC, Riyadh"


# --- nws._geo_tag: "USA, <state>" from areaDesc -------------------------
def test_geo_tag_reads_state_from_area_desc():
    assert nws._geo_tag("Travis, TX; Williamson, TX") == "USA, Texas"
    assert nws._geo_tag("Coastal Los Angeles County, CA") == "USA, California"


def test_geo_tag_first_state_when_multiple():
    assert nws._geo_tag("Cameron, LA; Jefferson, TX") == "USA, Louisiana"


def test_geo_tag_falls_back_to_usa_without_state():
    assert nws._geo_tag("Coastal waters out 10 nm") == "USA"


# --- nws._area_label: drop the repeated state on single-state alerts -----
def test_area_label_strips_state_when_single_state():
    # State is already in the "USA, Texas" tag, so it's dropped from the body.
    out = nws._area_label("Travis, TX; Williamson, TX; Hays, TX")
    assert "TX" not in out
    assert out == "Travis, Williamson, and Hays"


def test_area_label_keeps_state_when_multiple_states():
    # The tag can only name one state, so multi-state lists keep ', ST'.
    out = nws._area_label("Cameron, LA; Jefferson, TX")
    assert "LA" in out and "TX" in out


# --- nws._is_excluded: drop territory-only alerts ------------------------
_EXC = {"PR", "VI", "GU", "AS", "MP"}


def test_is_excluded_drops_territory_only_alert():
    assert nws._is_excluded("Mayaguez and Vicinity, PR", _EXC)
    assert nws._is_excluded("St. Thomas, VI; St. John, VI", _EXC)


def test_is_excluded_keeps_mainland_and_mixed():
    assert not nws._is_excluded("Travis, TX", _EXC)
    assert not nws._is_excluded("Travis, TX; San Juan, PR", _EXC)  # mixed -> keep
    assert not nws._is_excluded("Coastal waters out 10 nm", _EXC)  # no code -> keep
    assert not nws._is_excluded("Travis, TX", set())               # nothing excluded


# --- nws._tier -----------------------------------------------------------
def test_tier_critical_event():
    assert nws._tier("Tornado Warning") == "critical"


def test_tier_flash_flood_is_not_critical():
    """We deliberately removed Flash Flood from CRITICAL_EVENTS so it can't
    dominate the feed — guard against it sneaking back in."""
    assert nws._tier("Flash Flood Warning") == "serious"


def test_tier_advisory_suffix():
    assert nws._tier("Heat Advisory") == "advisory"


# --- nws._topic ----------------------------------------------------------
def test_topic_mapping():
    assert nws._topic("Flash Flood Warning") == "flood"
    assert nws._topic("Tornado Warning") == "tornado"
    assert nws._topic("Extreme Heat Warning") == "heat"
    # Marine warnings map via the sea/wind keywords.
    assert nws._topic("Gale Warning") == "marine"
    assert nws._topic("High Surf Warning") == "marine"
    # Small Craft Advisory has no marine keyword, so _topic returns "weather" —
    # harmless, because the SCA roundup signal sets topic="marine" explicitly and
    # individual SCAs are never routed through _topic.
    assert nws._topic("Small Craft Advisory") == "weather"


# --- nws.EVENT_FLOOR sanity (the pure-severity safety net) ---------------
def test_event_floor_keeps_lifethreat_high():
    for ev in ("Tornado Warning", "Hurricane Warning", "Storm Surge Warning"):
        assert nws.EVENT_FLOOR[ev] >= 95
    # Official marine warnings floored to match the modeled marine scale.
    assert nws.EVENT_FLOOR["Gale Warning"] == 74
    assert nws.EVENT_FLOOR["Hurricane Force Wind Warning"] == 95


# --- meteoalarm._hazard / _classify / _eu_topic --------------------------
def test_hazard_strips_colour_and_warning():
    assert meteoalarm._hazard("Severe thunderstorm warning") == "thunderstorm"


def test_hazard_handles_warning_for_phrasing():
    assert meteoalarm._hazard("warning for heatwave") == "heatwave"


def test_classify_maps_forest_to_fire_topic():
    token, _actions = meteoalarm._classify("Forest fire warning")
    assert token == "forest"
    assert meteoalarm._eu_topic(token) == "fire"


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
