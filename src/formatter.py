"""Assemble final tweet text: timestamped advisory body + hashtags."""
from __future__ import annotations

from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

from .sources import Signal

MAX_LEN = 280


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
    hour = now.strftime("%I").lstrip("0") or "12"
    minute = now.strftime("%M")
    ampm = now.strftime("%p").lower()
    label = now.strftime("%Z") if tzinfo is not timezone.utc else "UTC"
    return f"{hour}:{minute} {ampm} {label}:"


def render(signal: Signal) -> str:
    """Prepend the local timestamp, append hashtags, and clamp to 280 chars."""
    body = f"{timestamp(signal.tz)} {signal.text.strip()}"
    tags = " ".join(dict.fromkeys(signal.hashtags))  # de-dupe, keep order
    if not tags:
        return body[:MAX_LEN]

    room = MAX_LEN - len(tags) - 1  # 1 for the joining newline
    if len(body) > room:
        body = body[: room - 1].rstrip() + "…"
    return f"{body}\n{tags}"
