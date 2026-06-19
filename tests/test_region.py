"""Region scope filter: coordinate boxes and NGA keyword matching."""
from src import region


# --- in_scope: coordinates inside USA / Europe / Gulf --------------------
def test_in_scope_usa():
    assert region.in_scope(39.7, -104.9)   # Denver


def test_in_scope_europe():
    assert region.in_scope(51.9, 4.5)      # Rotterdam


def test_in_scope_gulf():
    assert region.in_scope(25.2, 55.3)     # Dubai


def test_out_of_scope():
    assert not region.in_scope(-33.9, 151.2)   # Sydney
    assert not region.in_scope(35.7, 139.7)    # Tokyo


def test_in_scope_handles_none_and_garbage():
    assert not region.in_scope(None, None)
    assert not region.in_scope("x", "y")


# --- text_in_scope: NGA region keywords ----------------------------------
def test_text_in_scope_matches_keyword():
    assert region.text_in_scope("PERSIAN GULF, off the coast")
    assert region.text_in_scope("North Sea approaches")     # case-insensitive


def test_text_in_scope_rejects_unknown_sea():
    assert not region.text_in_scope("SOUTH CHINA SEA near the reef")


def test_text_in_scope_empty():
    assert not region.text_in_scope("")
    assert not region.text_in_scope(None)
