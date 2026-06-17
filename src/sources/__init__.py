"""Signal sources for K5Bearing."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


def pick(options: list[str], seed: str) -> str:
    """Choose one phrasing deterministically from a seed.

    Same seed -> same choice (so a given alert always renders identically),
    different seeds -> spread across the options (so the feed reads varied).
    """
    if not options:
        return ""
    if len(options) == 1:
        return options[0]
    h = int(hashlib.md5(str(seed).encode("utf-8")).hexdigest(), 16)
    return options[h % len(options)]


@dataclass
class Signal:
    """A candidate post.

    severity: 0-100, used to rank when more candidates exist than the
    per-run budget allows. dedup_key must be stable for "the same" event.
    """

    category: str          # e.g. "geomagnetic", "solar", "weather", "digest"
    severity: int
    text: str              # tweet body (<= 280 chars after hashtags)
    dedup_key: str
    hashtags: list[str] = field(default_factory=list)
    tz: str | None = None  # IANA zone for the timestamp; None = UTC (global signals)
    # Voice tier, set by the source from the *kind* of alert (not raw severity):
    #   "critical" -> life-threatening, gets an "Act now, do not wait." close
    #   "serious"  -> default, posts as written
    #   "advisory" -> low-stakes, softened with a "Heads up," lead
    tier: str = "serious"
