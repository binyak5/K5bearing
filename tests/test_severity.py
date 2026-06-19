"""Cross-source severity-scale invariants.

Ranking is now pure-severity, so the *numbers* encode priority. These lock in
the coherent scale we built so a future tweak can't silently break the ordering.
"""
from src.sources import nws, meteoalarm, gdacs, marine


def test_meteoalarm_severity_ordered():
    w = meteoalarm.SEVERITY_WEIGHT
    assert w["Moderate"] < w["Severe"] < w["Extreme"]


def test_gdacs_red_outranks_orange():
    assert gdacs.ALERT_WEIGHT["Red"] > gdacs.ALERT_WEIGHT["Orange"]


def test_nws_severity_weights_ordered():
    w = nws.SEVERITY_WEIGHT
    assert w["Minor"] < w["Moderate"] < w["Severe"] < w["Extreme"]


def test_lifethreat_floors_outrank_serious_floors():
    f = nws.EVENT_FLOOR
    lifethreat = min(f["Tornado Warning"], f["Hurricane Warning"], f["Storm Surge Warning"])
    serious = max(f["Flash Flood Warning"], f["Severe Thunderstorm Warning"])
    assert lifethreat > serious


def test_official_marine_warnings_match_modeled_scale():
    """Fix we made: the authoritative NWS marine warning must never rank below
    the Open-Meteo-derived equivalent for the same conditions."""
    assert nws.EVENT_FLOOR["Hurricane Force Wind Warning"] == marine._wind_category(70)[1]
    assert nws.EVENT_FLOOR["Gale Warning"] == marine._wind_category(40)[1]
    assert nws.EVENT_FLOOR["Storm Warning"] == marine._wind_category(50)[1]


def test_eu_orange_sits_below_us_floored_events():
    """Fix we made: MeteoAlarm orange shouldn't beat the US floored events."""
    assert meteoalarm.SEVERITY_WEIGHT["Severe"] < nws.EVENT_FLOOR["Flash Flood Warning"]


def test_extreme_tiers_cluster_at_top():
    tops = [
        meteoalarm.SEVERITY_WEIGHT["Extreme"],
        gdacs.ALERT_WEIGHT["Red"],
        nws.EVENT_FLOOR["Tornado Warning"],
        marine._category(10.0)[1],
    ]
    assert all(t >= 95 for t in tops)
