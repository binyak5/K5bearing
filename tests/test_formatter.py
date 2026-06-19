"""Formatter: timestamp prefix, country code, voice tier, and length fitting."""
import re

from src.formatter import (
    _split_so,
    _pretty_zone,
    _apply_tier,
    _fit,
    render,
    fingerprint,
    MAX_LEN,
)
from src.sources import Signal


def _sig(text, **kw):
    kw.setdefault("category", "weather")
    kw.setdefault("severity", 80)
    kw.setdefault("dedup_key", "k")
    return Signal(text=text, **kw)


# --- _split_so: ", so X" -> ". X" (X capitalised) -------------------------
def test_split_so_rewrites_join():
    assert _split_so("Seas are building, so secure now.") == "Seas are building. Secure now."


def test_split_so_leaves_plain_text():
    assert _split_so("Conditions are rough. Stay alert.") == "Conditions are rough. Stay alert."


# --- _pretty_zone: numeric offsets -> UTC+X, named zones pass through ------
def test_pretty_zone_numeric():
    assert _pretty_zone("+08") == "UTC+8"
    assert _pretty_zone("-0530") == "UTC-5:30"


def test_pretty_zone_named_passthrough():
    assert _pretty_zone("CEST") == "CEST"
    assert _pretty_zone("EDT") == "EDT"


# --- _apply_tier: advisory softening --------------------------------------
def test_advisory_gets_heads_up_lead_and_lowercase():
    out = _apply_tier("A high surf advisory is active.", "advisory")
    assert out == "Heads up, a high surf advisory is active."


def test_advisory_keeps_acronym_caps():
    out = _apply_tier("UV is extreme today.", "advisory")
    assert out.startswith("Heads up, UV")


def test_serious_unchanged():
    text = "A tornado warning is active."
    assert _apply_tier(text, "serious") == text


# --- render: prefix shape + country code ----------------------------------
PREFIX = re.compile(r"^\d{2}:\d{2} \S+")


def test_render_has_time_prefix():
    out = render(_sig("A flood warning is active for X."))
    assert PREFIX.match(out)


def test_render_includes_country_code():
    out = render(_sig("A red wind warning is active for X.", tz="Europe/Zurich", country="CH"))
    # "HH:MM CEST CH: ..." — the code sits right before the colon.
    assert re.search(r"\d{2}:\d{2} \S+ CH: ", out)


def test_render_without_country_has_no_trailing_code():
    out = render(_sig("A geomagnetic storm is underway.", country=""))
    assert re.search(r"\d{2}:\d{2} \S+: ", out)
    assert " : " not in out


def test_render_applies_advisory_lead():
    out = render(_sig("a heat advisory is active.", tier="advisory"))
    assert "Heads up," in out


# --- _fit: never exceed MAX_LEN, never cut mid-sentence -------------------
def test_fit_trims_whole_sentences():
    body = "First sentence is here. " + ("Second sentence padding. " * 40)
    out = _fit("PFX ", body)
    assert len(out) <= MAX_LEN
    # Whatever survives ends on a sentence boundary (no dangling half-word).
    assert out.rstrip().endswith(".")


def test_fit_short_text_untouched():
    assert _fit("PFX ", "Short body.") == "PFX Short body."


# --- fingerprint: stable across numbers, distinct across wording ----------
def test_fingerprint_ignores_numbers():
    a = _sig("Seas are building to 4m in the North Sea.")
    b = _sig("Seas are building to 7m in the North Sea.")
    assert fingerprint(a) == fingerprint(b)


def test_fingerprint_differs_on_wording():
    a = _sig("A tornado warning is active for Travis.")
    b = _sig("A flood warning is active for Travis.")
    assert fingerprint(a) != fingerprint(b)
