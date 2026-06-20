"""Media card: region resolution + card_for rendering."""
from src.sources import Signal
from src import card, cardmap


def _sig(**cardkw):
    return Signal(category="earthquake", severity=90, text="t", dedup_key="k",
                  tz="America/Los_Angeles", card=(cardkw or None))


# --- region_for: coordinate -> card region code -------------------------
def test_region_for_maps_each_region():
    assert cardmap.region_for(40.3, -124.5) == "USA"   # Eureka, CA
    assert cardmap.region_for(38.2, 23.9) == "EU"       # near Athens
    assert cardmap.region_for(24.7, 46.7) == "GCC"      # Riyadh


def test_region_for_out_of_scope():
    assert cardmap.region_for(-33.9, 151.2) is None     # Sydney
    assert cardmap.region_for(35.7, 139.7) is None       # Tokyo


# --- card_for ------------------------------------------------------------
def test_card_for_none_without_card_data():
    assert card.card_for(Signal(category="x", severity=90, text="t", dedup_key="k")) is None


def test_card_for_renders_full_size_with_map():
    img = card.card_for(_sig(value="M 6.4", event="Earthquake",
                             detail="92 km SW of Eureka, CA", lat=40.3, lon=-124.5))
    assert img is not None
    assert img.size == (1600, 900)


def test_card_for_renders_without_coordinates():
    # No lat/lon -> no map, but still a valid card.
    img = card.card_for(_sig(value="G2", event="Geomagnetic storm", detail="global"))
    assert img is not None
    assert img.size == (1600, 900)


# --- on_land: land places get a map, open sea does not ------------------
def test_on_land_true_for_cities_and_coastal_piers():
    assert cardmap.on_land(25.20, 55.27)    # Dubai
    assert cardmap.on_land(24.71, 46.68)    # Riyadh
    assert cardmap.on_land(32.87, -117.25)  # San Diego HAB pier (just offshore)
    assert cardmap.on_land(40.80, -124.16)  # onshore quake, Eureka


def test_on_land_false_for_open_sea():
    assert not cardmap.on_land(56.0, 3.0)     # North Sea
    assert not cardmap.on_land(50.0, -1.0)    # English Channel
    assert not cardmap.on_land(40.80, -124.90)  # offshore quake
    assert not cardmap.on_land(30.0, -45.0)   # mid-Atlantic
