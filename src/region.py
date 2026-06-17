"""Regional scope filter — restrict global feeds to the regions we cover.

USA, Europe, and the Persian/Arabian Gulf states. Coordinate-based for the
feeds that give lat/lon (earthquakes, GDACS, marine), keyword-based for NGA
maritime warnings (which only give a named sea/region).
"""
from __future__ import annotations

# Rough lat/lon bounding boxes per region: (lat_min, lat_max, lon_min, lon_max).
BOXES = {
    "usa": (15.0, 72.0, -170.0, -64.0),    # CONUS + Alaska + Hawaii + territories
    "europe": (34.0, 72.0, -25.0, 45.0),   # Iceland to the Caucasus, Med to Arctic
    "gulf": (12.0, 33.0, 32.0, 62.0),      # Red Sea / Arabian Peninsula / Persian Gulf
}

# Region/sea keywords that count as in-scope for the NGA maritime feed.
NGA_KEYWORDS = {
    # US waters
    "GULF OF MEXICO", "WESTERN NORTH ATLANTIC", "CARIBBEAN", "EASTERN PACIFIC",
    "GULF OF ALASKA", "BERING", "ALASKA", "HAWAII", "GREAT LAKES", "FLORIDA",
    "CALIFORNIA", "CHESAPEAKE", "GULF OF MAINE", "PUERTO RICO",
    # European waters
    "MEDITERRANEAN", "NORTH SEA", "BALTIC", "BAY OF BISCAY", "ADRIATIC",
    "AEGEAN", "BLACK SEA", "ENGLISH CHANNEL", "IRISH SEA", "NORWEGIAN",
    "CELTIC", "IBERIAN", "TYRRHENIAN", "IONIAN",
    # Gulf waters
    "PERSIAN GULF", "ARABIAN GULF", "GULF OF OMAN", "ARABIAN SEA", "RED SEA",
    "GULF OF ADEN", "STRAIT OF HORMUZ",
    # Strategic chokepoints (in/bordering our regions)
    "GIBRALTAR", "BOSPORUS", "BOSPHORUS", "DARDANELLES", "SUEZ",
    "BAB-EL-MANDEB", "BAB EL MANDEB", "STRAIT OF DOVER", "KERCH",
}


def in_scope(lat: float | None, lon: float | None) -> bool:
    """True if the coordinate falls in USA, Europe, or the Gulf."""
    if lat is None or lon is None:
        return False
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    for lo_lat, hi_lat, lo_lon, hi_lon in BOXES.values():
        if lo_lat <= lat <= hi_lat and lo_lon <= lon <= hi_lon:
            return True
    return False


def text_in_scope(text: str) -> bool:
    """True if a maritime region/text references an in-scope sea or area."""
    upper = (text or "").upper()
    return any(kw in upper for kw in NGA_KEYWORDS)
