"""Assemble final tweet text: timestamped advisory body + hashtags."""
from __future__ import annotations

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
