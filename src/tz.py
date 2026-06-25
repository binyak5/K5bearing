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

# MeteoAlarm country slug -> ISO 3166-1 alpha-2 code (the "official"
# abbreviation shown after the timezone, e.g. Switzerland -> CH).
COUNTRY_CODES = {
    "andorra": "AD", "austria": "AT", "belgium": "BE", "bosnia-herzegovina": "BA",
    "bulgaria": "BG", "croatia": "HR", "cyprus": "CY", "czechia": "CZ",
    "denmark": "DK", "estonia": "EE", "finland": "FI", "france": "FR",
    "germany": "DE", "greece": "GR", "hungary": "HU", "iceland": "IS",
    "ireland": "IE", "israel": "IL", "italy": "IT", "latvia": "LV",
    "lithuania": "LT", "luxembourg": "LU", "malta": "MT", "moldova": "MD",
    "montenegro": "ME", "netherlands": "NL", "north-macedonia": "MK",
    "norway": "NO", "poland": "PL", "portugal": "PT", "romania": "RO",
    "serbia": "RS", "slovakia": "SK", "slovenia": "SI", "spain": "ES",
    "sweden": "SE", "switzerland": "CH", "ukraine": "UA", "united-kingdom": "GB",
}

# IANA zone -> ISO alpha-2, for the coordinate-based sources (Gulf cities, the
# Rotterdam city update) that carry a timezone rather than a country slug.
ZONE_CODES = {
    "Asia/Dubai": "AE", "Asia/Riyadh": "SA", "Asia/Qatar": "QA",
    "Asia/Bahrain": "BH", "Asia/Kuwait": "KW", "Asia/Muscat": "OM",
    "Europe/Amsterdam": "NL",
}

# MeteoAlarm country slug -> (lat, lon) of the capital. A fixed, reliable anchor
# for the European temperature approximation: the feed gives no coordinates, and
# geocoding region names is hopeless (it resolves Dutch provinces to US towns),
# so we forecast the heat/cold at the capital — a sound proxy for a country-wide
# warning. (Hard-coded, not geocoded, so it can never resolve to the wrong place.)
COUNTRY_COORDS = {
    "andorra": (42.51, 1.52), "austria": (48.21, 16.37), "belgium": (50.85, 4.35),
    "bosnia-herzegovina": (43.86, 18.41), "bulgaria": (42.70, 23.32),
    "croatia": (45.81, 15.98), "cyprus": (35.17, 33.36), "czechia": (50.08, 14.44),
    "denmark": (55.68, 12.57), "estonia": (59.44, 24.75), "finland": (60.17, 24.94),
    "france": (48.85, 2.35), "germany": (52.52, 13.40), "greece": (37.98, 23.73),
    "hungary": (47.50, 19.04), "iceland": (64.15, -21.94), "ireland": (53.35, -6.26),
    "israel": (31.77, 35.21), "italy": (41.90, 12.50), "latvia": (56.95, 24.11),
    "lithuania": (54.69, 25.28), "luxembourg": (49.61, 6.13), "malta": (35.90, 14.51),
    "moldova": (47.01, 28.86), "montenegro": (42.44, 19.26), "netherlands": (52.37, 4.90),
    "north-macedonia": (41.99, 21.43), "norway": (59.91, 10.75), "poland": (52.23, 21.01),
    "portugal": (38.72, -9.14), "romania": (44.43, 26.10), "serbia": (44.79, 20.45),
    "slovakia": (48.15, 17.11), "slovenia": (46.06, 14.51), "spain": (40.42, -3.70),
    "sweden": (59.33, 18.07), "switzerland": (46.95, 7.45), "ukraine": (50.45, 30.52),
    "united-kingdom": (51.51, -0.13),
}


def country_coords(slug: str) -> tuple[float, float] | None:
    """Capital (lat, lon) for a MeteoAlarm country slug, or None if unknown."""
    return COUNTRY_COORDS.get((slug or "").lower())

# ISO alpha-2 -> (continent, full country name), for the geographic tag printed
# after the timezone in each post, e.g. 'CEST Europe, France:'. Covers every
# country the sources can stamp: the US (NWS), the MeteoAlarm European network,
# and the Gulf states. Continent follows geography (the Gulf states and Israel
# are in Asia); anything unmapped falls back to the bare code.
COUNTRY_INFO = {
    "US": ("North America", "United States"),
    # Europe (MeteoAlarm network + the Rotterdam city update)
    "AD": ("Europe", "Andorra"), "AT": ("Europe", "Austria"),
    "BE": ("Europe", "Belgium"), "BA": ("Europe", "Bosnia and Herzegovina"),
    "BG": ("Europe", "Bulgaria"), "HR": ("Europe", "Croatia"),
    "CY": ("Europe", "Cyprus"), "CZ": ("Europe", "Czechia"),
    "DK": ("Europe", "Denmark"), "EE": ("Europe", "Estonia"),
    "FI": ("Europe", "Finland"), "FR": ("Europe", "France"),
    "DE": ("Europe", "Germany"), "GR": ("Europe", "Greece"),
    "HU": ("Europe", "Hungary"), "IS": ("Europe", "Iceland"),
    "IE": ("Europe", "Ireland"), "IT": ("Europe", "Italy"),
    "LV": ("Europe", "Latvia"), "LT": ("Europe", "Lithuania"),
    "LU": ("Europe", "Luxembourg"), "MT": ("Europe", "Malta"),
    "MD": ("Europe", "Moldova"), "ME": ("Europe", "Montenegro"),
    "NL": ("Europe", "Netherlands"), "MK": ("Europe", "North Macedonia"),
    "NO": ("Europe", "Norway"), "PL": ("Europe", "Poland"),
    "PT": ("Europe", "Portugal"), "RO": ("Europe", "Romania"),
    "RS": ("Europe", "Serbia"), "SK": ("Europe", "Slovakia"),
    "SI": ("Europe", "Slovenia"), "ES": ("Europe", "Spain"),
    "SE": ("Europe", "Sweden"), "CH": ("Europe", "Switzerland"),
    "UA": ("Europe", "Ukraine"), "GB": ("Europe", "United Kingdom"),
    # Asia (Gulf states + Israel)
    "IL": ("Asia", "Israel"), "AE": ("Asia", "United Arab Emirates"),
    "SA": ("Asia", "Saudi Arabia"), "QA": ("Asia", "Qatar"),
    "BH": ("Asia", "Bahrain"), "KW": ("Asia", "Kuwait"),
    "OM": ("Asia", "Oman"),
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


def code_for_country(slug: str) -> str | None:
    """ISO alpha-2 code for a MeteoAlarm country slug ('switzerland' -> 'CH')."""
    return COUNTRY_CODES.get((slug or "").lower())


def code_for_zone(zone: str) -> str | None:
    """ISO alpha-2 code for an IANA timezone ('Asia/Dubai' -> 'AE')."""
    return ZONE_CODES.get(zone or "")


def country_name(code: str | None) -> str | None:
    """ISO alpha-2 code -> full country name ('FR' -> 'France'), or None."""
    info = COUNTRY_INFO.get((code or "").upper())
    return info[1] if info else None


# US state / territory abbreviation -> full name, for the "USA, <state>" geo tag
# parsed out of NWS areaDesc ("Travis, TX; ..." -> "Texas").
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "Washington, D.C.",
    "PR": "Puerto Rico", "VI": "U.S. Virgin Islands", "GU": "Guam",
    "AS": "American Samoa", "MP": "Northern Mariana Islands",
}


def state_name(abbr: str | None) -> str | None:
    """US state abbreviation -> full name ('TX' -> 'Texas'), or None."""
    return US_STATES.get((abbr or "").upper())


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
