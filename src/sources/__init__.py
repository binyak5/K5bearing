"""Signal sources for K5Bearing."""
from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field


def gather(fn, items: list, workers: int = 12) -> list:
    """Run fn over items concurrently and flatten the results into one list.

    The sources are almost entirely network-bound (one or more HTTP calls per
    watched location/area), so doing them sequentially makes a run take
    minutes. A small thread pool collapses that to roughly the slowest single
    item. fn may return a Signal, a list of Signals, or None.
    """
    results: list = []
    if not items:
        return results
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        for r in pool.map(fn, items):
            if r is None:
                continue
            results.extend(r if isinstance(r, list) else [r])
    return results


def region_list(names, budget: int = 130) -> str:
    """Join area/region names into a readable list, naming as many as fit in
    ~budget chars, then 'and N other areas' for the rest. Used so posts say
    *where* (the actual regions) rather than just a country or a count.
    """
    names = [n for n in dict.fromkeys(n for n in names if n)]  # de-dupe, keep order
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    chosen: list[str] = []
    for n in names:
        if chosen and len(", ".join(chosen + [n])) > budget:
            break
        chosen.append(n)
    remaining = len(names) - len(chosen)
    if remaining > 0:
        return ", ".join(chosen) + f", and {remaining} other area" + ("s" if remaining != 1 else "")
    if len(chosen) == 2:
        return f"{chosen[0]} and {chosen[1]}"
    return ", ".join(chosen[:-1]) + f", and {chosen[-1]}"


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
    #   "advisory" -> low-stakes, softened with a "Heads up," lead
    #   anything else ("serious"/"critical") -> posts as written
    tier: str = "serious"
    # Coarse subject ("flood", "wind", "heat"...) used to avoid posting the same
    # topic twice in a row. Falls back to `category` when left blank.
    topic: str = ""
    # ISO 3166-1 alpha-2 country code (e.g. "CH", "US", "AE"), shown right after
    # the timezone in the timestamp prefix. Blank for country-less signals
    # (space weather, open-sea marine areas, multi-country navigation warnings).
    country: str = ""
    # Optional media-card data. When set (by sources that have a clean headline
    # value + coordinates), the poster can render and attach a card image:
    #   {"value", "event", "detail", "meta", "lat", "lon"}
    # lat/lon drive the dotted-map region + orange dot; omit them for a no-map card.
    card: dict | None = None
