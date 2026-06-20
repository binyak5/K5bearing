"""Faint dotted-landmass background for a card: a sparse white dot grid over the
land around the event, with a glowing orange dot pinned to a fixed on-card anchor.

The map is centred on the event coordinate at a fixed zoom, so the locator dot
always lands in the same clear spot (out to the right of the left-aligned type)
with recognisable local geography around it — instead of a whole-continent view
where the dot can fall behind the text or get lost. Geography comes from a bundled
simplified world GeoJSON (no runtime fetch).
"""
from __future__ import annotations

import json
from math import cos, radians
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

GEOJSON = Path(__file__).resolve().parent.parent / "assets" / "geo" / "countries.geo.json"

# region.BOXES key -> the card's region code (used for the {region} label, not the map).
_REGION_KEY = {"usa": "USA", "europe": "EU", "gulf": "GCC"}

# Event-centred view: the event sits at this fraction of (W, H) and the map shows
# this many degrees of latitude across the full card height (smaller = more
# zoomed-in / more local). The anchor sits in the lower-right open area, below the
# left-aligned headline block (which runs to roughly 0.68 H), so the locator dot is
# never painted over by a long value like "LIGHTNING".
ANCHOR_X_FRAC = 0.72
ANCHOR_Y_FRAC = 0.80
DEG_PER_HEIGHT = 32.0

DOT_STEP = 21            # px between land dots
DOT_R = 2                # land-dot radius
DOT_FILL = (255, 255, 255, 38)   # faint white texture

ORANGE = (255, 106, 0)

_rings: list[tuple[tuple[float, float, float, float], list[tuple[float, float]]]] | None = None


def region_for(lat: float, lon: float) -> str | None:
    """Card region code (USA/EU/GCC) for a coordinate, or None if out of scope."""
    from . import region
    for name, (la0, la1, lo0, lo1) in region.BOXES.items():
        if la0 <= lat <= la1 and lo0 <= lon <= lo1:
            return _REGION_KEY.get(name)
    return None


def on_land(lat: float, lon: float, pad: float = 0.15) -> bool:
    """True if the coordinate is on (or within ~16 km of) land — a real place
    like a city, state, or country — rather than open sea.

    This is what decides whether a card gets a map: a land location does, an
    open-sea one (high seas, swell, marine fog, offshore/mid-ocean quakes) does
    not. The small pad keeps coastal piers and harbour towns, whose point can
    fall just offshore of the simplified coastline, on the land side.
    """
    for dla in (-pad, 0.0, pad):
        for dlo in (-pad, 0.0, pad):
            la, lo = lat + dla, lon + dlo
            for bb, ring in _load_rings():
                if bb[0] <= lo <= bb[2] and bb[1] <= la <= bb[3] and _point_in_ring(lo, la, ring):
                    return True
    return False


def _load_rings():
    """Outer rings of every country as (bbox, [(lon,lat)...]); loaded once."""
    global _rings
    if _rings is not None:
        return _rings
    data = json.loads(GEOJSON.read_text())
    rings: list = []
    for feat in data.get("features", []):
        geom = feat.get("geometry") or {}
        polys = []
        if geom.get("type") == "Polygon":
            polys = [geom["coordinates"]]
        elif geom.get("type") == "MultiPolygon":
            polys = geom["coordinates"]
        for poly in polys:
            ring = [(float(p[0]), float(p[1])) for p in poly[0]]
            xs = [p[0] for p in ring]
            ys = [p[1] for p in ring]
            rings.append(((min(xs), min(ys), max(xs), max(ys)), ring))
    _rings = rings
    return rings


def _point_in_ring(lon: float, lat: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _projector(lat0: float, lon0: float, W: int, H: int):
    """Equirectangular projection centred on (lat0, lon0): the event maps to the
    fixed anchor, with cos(lat) longitude correction so the land keeps its shape."""
    scale_y = H / DEG_PER_HEIGHT
    scale_x = scale_y * cos(radians(lat0))
    ax, ay = ANCHOR_X_FRAC * W, ANCHOR_Y_FRAC * H

    def to_xy(lat, lon):
        return ax + (lon - lon0) * scale_x, ay - (lat - lat0) * scale_y

    def to_ll(x, y):
        return lat0 - (y - ay) / scale_y, lon0 + (x - ax) / scale_x
    return to_xy, to_ll, ax, ay


def _dotted_layer(lat0: float, lon0: float, W: int, H: int) -> Image.Image:
    _, to_ll, _ax, _ay = _projector(lat0, lon0, W, H)
    corners = [to_ll(0, 0), to_ll(W, 0), to_ll(0, H), to_ll(W, H)]
    lats = [c[0] for c in corners]
    lons = [c[1] for c in corners]
    lat_min, lat_max, lon_min, lon_max = min(lats), max(lats), min(lons), max(lons)
    cand = [(bb, r) for bb, r in _load_rings()
            if not (bb[2] < lon_min or bb[0] > lon_max or bb[3] < lat_min or bb[1] > lat_max)]

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for py in range(0, H, DOT_STEP):
        for px in range(0, W, DOT_STEP):
            lat, lon = to_ll(px, py)
            for bb, ring in cand:
                if bb[0] <= lon <= bb[2] and bb[1] <= lat <= bb[3] and _point_in_ring(lon, lat, ring):
                    d.ellipse((px - DOT_R, py - DOT_R, px + DOT_R, py + DOT_R), fill=DOT_FILL)
                    break
    return layer


def _glow(x: float, y: float, W: int, H: int) -> Image.Image:
    """A soft, blurred orange glow with a small bright core, on its own layer."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(layer)
    g.ellipse((x - 40, y - 40, x + 40, y + 40), fill=(*ORANGE, 52))   # wide halo
    g.ellipse((x - 20, y - 20, x + 20, y + 20), fill=(*ORANGE, 88))   # inner bloom
    layer = layer.filter(ImageFilter.GaussianBlur(19))
    g = ImageDraw.Draw(layer)
    g.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(*ORANGE, 205))      # crisp core
    return layer


def background(lat: float, lon: float, W: int, H: int) -> Image.Image:
    """RGBA overlay: dotted land around the event + a glowing orange dot pinned to
    the fixed anchor (where the event is centred)."""
    overlay = _dotted_layer(lat, lon, W, H)
    _, _, ax, ay = _projector(lat, lon, W, H)
    return Image.alpha_composite(overlay, _glow(ax, ay, W, H))
