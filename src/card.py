"""Render a media card for a signal: pure-black background, white Eurostile
Extended text, no hashtags. One consistent template — the same element slots in
the same places every time, only the values change.

The card is a PNG attached to high-severity posts. Text auto-fits the card width
so a long location never overflows (Eurostile Extended is very wide).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import cardmap

FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "EurostileExtendedBlack.ttf"
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "k5bearing-logo.png"
LOGO_ALPHA = 255        # match the text, which flattens to full white on RGB export
FOOTER_SIZE = 28        # the time eyebrow (top-left)
TOP_Y = 150             # vertical centre of the time eyebrow

W, H = 1600, 900            # 16:9, the size X renders inline
MARGIN = 110
BRAND_SIZE = 22         # @handle text in the top-right brand lockup
BRAND_LOGO_SIZE = 52    # compass mark height in the brand lockup
BRAND_LOGO_GAP = 14     # space between the @handle and the mark
BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)
DETAIL = (255, 255, 255, 205)   # slightly dimmed white
MUTED = (255, 255, 255, 110)    # labels / meta

LINE_GAP = 58    # uniform whitespace between every stacked line


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


_logo_cache: Image.Image | None = None


def _logo(alpha: int = LOGO_ALPHA) -> Image.Image:
    """The compass mark as transparent white (alpha from the white star), trimmed
    to its bounding box so it scales tightly and leaves no black box behind."""
    global _logo_cache
    if _logo_cache is None:
        gray = Image.open(LOGO_PATH).convert("L")
        gray = gray.crop(gray.getbbox())          # trim the black margin to the star
        white = Image.new("L", gray.size, 255)
        _logo_cache = Image.merge("RGBA", (white, white, white, gray))
    a = _logo_cache.getchannel("A").point(lambda v: v * alpha // 255)
    out = _logo_cache.copy()
    out.putalpha(a)
    return out


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_w: int, start: int, min_size: int) -> ImageFont.FreeTypeFont:
    """Largest font from `start` down to `min_size` whose text fits max_w."""
    size = start
    while size > min_size:
        f = _font(size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return _font(min_size)


def render_card(
    value: str,
    label: str,
    detail: str,
    time: str = "",
    handle: str = "@k5bearing",
    region: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> Image.Image:
    """Build the card image. All text is uppercased for the Eurostile look.

    label is the "{region} · {event}" header that sits above the value, e.g.
    "USA · EARTHQUAKE". handle is the account, top-right.

    If region (USA/EU/GCC) and lat/lon are given, a faint dotted map of that
    region is drawn behind the text with an orange dot at the event location.

    The four left-hand lines are stacked with one uniform gap and aligned by
    their *inked* left edge (correcting for each glyph's side bearing), so the
    first letter of every line sits on the same vertical.
    """
    img = Image.new("RGBA", (W, H), BLACK)
    if region is not None and lat is not None and lon is not None:
        img = Image.alpha_composite(img, cardmap.background(lat, lon, W, H))
    d = ImageDraw.Draw(img)
    content_w = W - 2 * MARGIN
    fs = _font(FOOTER_SIZE)

    # Time eyebrow at the top-left margin (centred on TOP_Y).
    if time.strip():
        tb = fs.getmask(time.upper()).getbbox()
        d.text((MARGIN - (tb[0] if tb else 0), TOP_Y), time.upper(), font=fs, fill=WHITE, anchor="lm")

    # Brand lockup in the top-right, paired with the time eyebrow as a header row:
    # compass mark at the right margin with the @handle to its left, centred on TOP_Y.
    bf = _font(BRAND_SIZE)
    logo = _logo()
    lw = round(BRAND_LOGO_SIZE * logo.width / logo.height)
    logo_x = W - MARGIN - lw
    # Centre the logo on the @handle's *inked* middle (cap centre), not the metric
    # middle, so the mark and the text line up exactly.
    hb = d.textbbox((logo_x - BRAND_LOGO_GAP, TOP_Y), handle.upper(), font=bf, anchor="rm")
    brand_cy = (hb[1] + hb[3]) / 2
    img.alpha_composite(logo.resize((lw, BRAND_LOGO_SIZE), Image.LANCZOS),
                        (logo_x, round(brand_cy - BRAND_LOGO_SIZE / 2)))
    d.text((logo_x - BRAND_LOGO_GAP, TOP_Y), handle.upper(), font=bf, fill=WHITE, anchor="rm")

    # Centred headline block: {region}|{event} · value · detail.
    rows = [
        (label.upper(), _fit_font(d, label.upper(), content_w, 62, 32), True),
        (value.upper(), _fit_font(d, value.upper(), content_w, 220, 70), False),
        (detail.upper(), _fit_font(d, detail.upper(), content_w, 54, 26), False),
    ]

    boxes = [d.textbbox((0, 0), text or " ", font=font, anchor="ls") for text, font, _ in rows]
    total_h = sum(b[3] - b[1] for b in boxes) + LINE_GAP * (len(rows) - 1)

    y_top = (H - total_h) / 2          # vertically centre the whole block
    for (text, font, is_label), (_left, top, _right, bottom) in zip(rows, boxes):
        baseline = y_top - top         # place this row's inked top at y_top
        if is_label and "·" in text:
            _draw_label(d, text, font, baseline, WHITE)
        elif text.strip():
            # textbbox reports left=0 (ignores the side bearing); measure the TRUE
            # inked left from the glyph mask so every first letter lands on MARGIN.
            mb = font.getmask(text).getbbox()
            d.text((MARGIN - (mb[0] if mb else 0), baseline), text, font=font, fill=WHITE, anchor="ls")
        y_top = baseline + bottom + LINE_GAP
    return img


def _draw_label(d: ImageDraw.ImageDraw, text: str, font, baseline: float, fill) -> None:
    """Draw "{region} · {event}" with a short vertical line instead of the dot,
    the region's first letter aligned to MARGIN like the other lines."""
    left, right = (s.strip() for s in text.split("·", 1))
    mb = font.getmask(left).getbbox()
    x = MARGIN - (mb[0] if mb else 0)
    d.text((x, baseline), left, font=font, fill=fill, anchor="ls")
    pen_end = x + d.textlength(left, font=font)
    cb = d.textbbox((0, 0), left, font=font, anchor="ls")
    cap_top, cap_bottom = baseline + cb[1], baseline + cb[3]
    inset = (cap_bottom - cap_top) * 0.12
    gap, line_w = 30, 6
    lx = pen_end + gap
    d.rectangle((lx, cap_top + inset, lx + line_w, cap_bottom - inset), fill=fill)
    d.text((lx + line_w + gap, baseline), right, font=font, fill=fill, anchor="ls")


def save_card(value: str, label: str, detail: str, out_path: str, time: str = "",
              handle: str = "@k5bearing", region: str | None = None,
              lat: float | None = None, lon: float | None = None) -> str:
    img = render_card(value, label, detail, time, handle, region, lat, lon)
    img.convert("RGB").save(out_path, "PNG")
    return out_path


def _eyebrow_time(tzname: str | None) -> str:
    """Local time eyebrow, e.g. '06:18 PDT', in the signal's timezone."""
    from .formatter import timestamp
    return timestamp(tzname).rstrip(": ").strip()


def card_for(signal) -> Image.Image | None:
    """Render a card for a signal that carries `card` data, else None.

    A map (dotted region + orange locator dot) is drawn only when the event is at
    a real land place — a city, state, or country. Open-sea events (high seas,
    swell, marine fog, offshore quakes) and coordinate-less ones (NGA warnings)
    render map-less: just the event, value, and place name. The region prefix in
    the label ("USA · EARTHQUAKE") goes with the map, so map-less cards show the
    event alone."""
    c = getattr(signal, "card", None)
    if not c:
        return None
    lat, lon = c.get("lat"), c.get("lon")
    show_map = lat is not None and lon is not None and cardmap.on_land(lat, lon)
    region = cardmap.region_for(lat, lon) if show_map else None
    event = c.get("event", "")
    label = f"{region} · {event}" if region else event
    return render_card(c.get("value", ""), label, c.get("detail", ""),
                       time=_eyebrow_time(getattr(signal, "tz", None)),
                       region=region,
                       lat=lat if show_map else None,
                       lon=lon if show_map else None)


def card_png_for(signal, out_path: str) -> str | None:
    """Render the signal's card to a PNG file; returns the path, or None if the
    signal has no card."""
    img = card_for(signal)
    if img is None:
        return None
    img.convert("RGB").save(out_path, "PNG")
    return out_path
