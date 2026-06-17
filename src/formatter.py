"""Assemble final tweet text: timestamped advisory body + hashtags."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

from .sources import Signal

MAX_LEN = 280

# Style rule: never join clauses with ", so ..." — split into two sentences,
# e.g. "Seas are building, so secure for heavy weather" ->
#      "Seas are building. Secure for heavy weather".
_SO_JOIN = re.compile(r", so (\w)")


def _split_so(text: str) -> str:
    return _SO_JOIN.sub(lambda m: ". " + m.group(1).upper(), text)


def _pretty_zone(label: str) -> str:
    """Turn a numeric offset abbreviation ('+08', '-0530') into 'UTC+8' /
    'UTC-5:30'. Named zones (EDT, CEST, BST) pass through unchanged.
    """
    if label[:1] in "+-":
        sign, digits = label[0], label[1:].replace(":", "")
        if digits.isdigit():
            hours = int(digits[:2])
            minutes = int(digits[2:4]) if len(digits) >= 4 else 0
            return f"UTC{sign}{hours}" + (f":{minutes:02d}" if minutes else "")
    return label


def timestamp(zone: str | None = None) -> str:
    """Advisory-style lead-in in the alert's local zone, e.g. 'Mon 2 am EDT:'.

    Falls back to UTC when no zone is given or it can't be loaded.
    """
    tzinfo = timezone.utc
    if zone and ZoneInfo is not None:
        try:
            tzinfo = ZoneInfo(zone)
        except Exception:
            tzinfo = timezone.utc
    now = datetime.now(tzinfo)
    label = _pretty_zone(now.strftime("%Z")) if tzinfo is not timezone.utc else "UTC"
    return f"{now.strftime('%H:%M')} {label}:"


def render(signal: Signal) -> str:
    """Prepend the local timestamp and clamp to 280 chars. No hashtags."""
    body = f"{timestamp(signal.tz)} {_split_so(signal.text.strip())}"
    if len(body) > MAX_LEN:
        body = body[: MAX_LEN - 1].rstrip() + "…"
    return body


# Numbers that drift run-to-run for the same event (a Kp of 5 then 6, seas at
# 4 m then 5 m) shouldn't read as a distinct alert, so the fingerprint keeps
# only letters. Place names and the alert wording — the parts that actually
# distinguish one event from another — are what's left.
_FP_STRIP = re.compile(r"[^a-z ]+")
_FP_WS = re.compile(r"\s+")


def fingerprint(signal: Signal) -> str:
    """A content hash of the alert body, independent of timestamp and numbers.

    Two signals that render to the same words (e.g. the same warning surfaced
    by two different sources, or under two different dedup-key formats) share a
    fingerprint, so the second one is suppressed even though its dedup_key
    differs. This is the backstop behind the per-source dedup_key.
    """
    text = _split_so(signal.text.strip()).lower()
    text = _FP_STRIP.sub(" ", text)
    text = _FP_WS.sub(" ", text).strip()
    return "fp:" + hashlib.md5(text.encode("utf-8")).hexdigest()[:16]
