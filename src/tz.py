"""Resolve the local timezone of an alert so each tweet is stamped in the
time zone where the event is actually happening (e.g. 'Mon 2 am EDT').

Coordinates -> IANA zone via timezonefinder (offline). MeteoAlarm gives no
coordinates, so European countries map to their primary zone. Anything we
can't resolve falls back to UTC, so this never raises.
"""
from __future__ import annotations

# MeteoAlarm country slug -> primary IANA timezone (mainland).
COUNTRY_ZONES = {
    "andorra": "Europe/Andorra",
    "austria": "Europe/Vienna",
    "belgium": "Europe/Brussels",
    "bosnia-herzegovina": "Europe/Sarajevo",
    "bulgaria": "Europe/Sofia",
    "croatia": "Europe/Zagreb",
    "cyprus": "Asia/Nicosia",
    "czechia": "Europe/Prague",
    "denmark": "Europe/Copenhagen",
    "estonia": "Europe/Tallinn",
    "finland": "Europe/Helsinki",
    "france": "Europe/Paris",
    "germany": "Europe/Berlin",
    "greece": "Europe/Athens",
    "hungary": "Europe/Budapest",
    "iceland": "Atlantic/Reykjavik",
    "ireland": "Europe/Dublin",
    "israel": "Asia/Jerusalem",
    "italy": "Europe/Rome",
    "latvia": "Europe/Riga",
    "lithuania": "Europe/Vilnius",
    "luxembourg": "Europe/Luxembourg",
    "malta": "Europe/Malta",
    "moldova": "Europe/Chisinau",
    "montenegro": "Europe/Podgorica",
    "netherlands": "Europe/Amsterdam",
    "north-macedonia": "Europe/Skopje",
    "norway": "Europe/Oslo",
    "poland": "Europe/Warsaw",
    "portugal": "Europe/Lisbon",
    "romania": "Europe/Bucharest",
    "serbia": "Europe/Belgrade",
    "slovakia": "Europe/Bratislava",
    "slovenia": "Europe/Ljubljana",
    "spain": "Europe/Madrid",
    "sweden": "Europe/Stockholm",
    "switzerland": "Europe/Zurich",
    "ukraine": "Europe/Kyiv",
    "united-kingdom": "Europe/London",
}

_finder = None


def _tf():
    global _finder
    if _finder is None:
        from timezonefinder import TimezoneFinder

        _finder = TimezoneFinder()
    return _finder


def zone_for_coords(lon: float, lat: float) -> str | None:
    try:
        return _tf().timezone_at(lng=float(lon), lat=float(lat))
    except Exception:
        return None


def zone_for_country(slug: str) -> str | None:
    return COUNTRY_ZONES.get((slug or "").lower())


def polygon_centroid(geometry: dict | None) -> tuple[float, float] | None:
    """Rough centroid (mean of vertices) of a GeoJSON Polygon/MultiPolygon."""
    if not geometry:
        return None
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if not coords:
        return None
    if gtype == "Polygon":
        ring = coords[0]
    elif gtype == "MultiPolygon":
        ring = coords[0][0]
    elif gtype == "Point":
        return float(coords[0]), float(coords[1])
    else:
        return None
    pts = [(p[0], p[1]) for p in ring if len(p) >= 2]
    if not pts:
        return None
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
