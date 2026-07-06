"""Cross-source severity-scale invariants.

Ranking is now pure-severity, so the *numbers* encode priority. These lock in
the coherent scale we built so a future tweak can't silently break the ordering.
The reusable weights now live in sources.wording (the old NWS scale, kept when
the US/EU sources were removed for the Rotterdam-only account).
"""
from src.sources import wording, gdacs, marine


def test_gdacs_red_outranks_orange():
    assert gdacs.ALERT_WEIGHT["Red"] > gdacs.ALERT_WEIGHT["Orange"]


def test_severity_weights_ordered():
    w = wording.SEVERITY_WEIGHT
    assert w["Minor"] < w["Moderate"] < w["Severe"] < w["Extreme"]


def test_lifethreat_floors_outrank_serious_floors():
    f = wording.EVENT_FLOOR
    lifethreat = min(f["Tornado Warning"], f["Hurricane Warning"], f["Storm Surge Warning"])
    serious = max(f["Flash Flood Warning"], f["Severe Thunderstorm Warning"])
    assert lifethreat > serious


def test_official_marine_warnings_match_modeled_scale():
    """The authoritative marine warning floors must match the Open-Meteo-derived
    equivalent for the same conditions, so one never ranks below the other."""
    assert wording.EVENT_FLOOR["Hurricane Force Wind Warning"] == marine._wind_category(70)[1]
    assert wording.EVENT_FLOOR["Gale Warning"] == marine._wind_category(40)[1]
    assert wording.EVENT_FLOOR["Storm Warning"] == marine._wind_category(50)[1]


def test_extreme_tiers_cluster_at_top():
    tops = [
        gdacs.ALERT_WEIGHT["Red"],
        wording.EVENT_FLOOR["Tornado Warning"],
        marine._category(10.0)[1],
    ]
    assert all(t >= 95 for t in tops)
