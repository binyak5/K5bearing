"""State: dedup TTL, per-category + daily caps, spacing, topic memory.

These are the inputs the main selection loop relies on, so they're the
highest-value behaviours to lock down. Each test uses a temp state file.
"""
from src.state import State


def _state(tmp_path):
    return State(path=tmp_path / "state.json")


# --- dedup --------------------------------------------------------------
def test_dedup_blocks_within_ttl(tmp_path):
    s = _state(tmp_path)
    assert not s.already_posted("k", 48)
    s.mark_posted("k")
    assert s.already_posted("k", 48)


def test_dedup_unknown_key(tmp_path):
    assert not _state(tmp_path).already_posted("never", 48)


# --- daily / monthly / category counters --------------------------------
def test_counters_increment(tmp_path):
    s = _state(tmp_path)
    assert s.posts_today() == 0
    s.increment_today("weather")
    s.increment_today("weather")
    s.increment_today("gulf")
    assert s.posts_today() == 3
    assert s.posts_this_month() == 3
    assert s.posts_today_in("weather") == 2
    assert s.posts_today_in("gulf") == 1
    assert s.posts_today_in("marine") == 0


# --- spacing ------------------------------------------------------------
def test_spacing_infinite_before_first_post(tmp_path):
    assert _state(tmp_path).minutes_since_last_post() == float("inf")


def test_spacing_zero_right_after_post(tmp_path):
    s = _state(tmp_path)
    s.mark_post_time()
    assert s.minutes_since_last_post() < 1


# --- topic memory -------------------------------------------------------
def test_last_topic_roundtrip(tmp_path):
    s = _state(tmp_path)
    assert s.last_topic() == ""
    s.set_last_topic("flood")
    assert s.last_topic() == "flood"


# --- persistence --------------------------------------------------------
def test_save_and_reload(tmp_path):
    p = tmp_path / "state.json"
    s = State(path=p)
    s.mark_posted("k")
    s.increment_today("weather")
    s.set_last_topic("heat")
    s.save()

    s2 = State(path=p)
    assert s2.already_posted("k", 48)
    assert s2.posts_today_in("weather") == 1
    assert s2.last_topic() == "heat"
