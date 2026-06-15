"""Signal sources for K5Bearing."""
from __future__ import annotations

from dataclasses import dataclass, field


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
