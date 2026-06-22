"""FIFA World Cup final scores, from ESPN's public, keyless scoreboard API.

We post the result the moment a knockout match goes final. Only knockout rounds
(Round of 32 onward) are posted — group-stage matches are never surfaced — which
is read straight from each event's `season.slug`, so it starts exactly when the
Round of 32 does. Penalty shootouts and extra time are reflected in the wording.

Driven by a dedicated fast workflow (see .github/workflows/worldcup.yml), not the
main 30-minute pipeline, so a score lands within minutes of full time.
"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

from ..config import USER_AGENT
from . import Signal

SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
TIMEOUT = 20

# ESPN event season.slug -> the round name we print. Only these (knockouts) are
# posted; any other slug (group stage) is ignored, so scores begin at the R32.
KNOCKOUT_ROUNDS = {
    "round-of-32": "Round of 32",
    "round-of-16": "Round of 16",
    "quarterfinals": "Quarter final",
    "semifinals": "Semi final",
    "3rd-place": "Third place playoff",
    "third-place": "Third place playoff",
    "final": "Final",
}


def _parse_iso(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _score_text(home: dict, away: dict, round_name: str, detail: str) -> str:
    """A result line, e.g.:
        'Full time - Netherlands 3–1 United States (Round of 16)'
        'Full time (AET) - Argentina 2–2 France - 4–2 penalties (Final)'
    Penalty score is in the same home–away order as the result line.
    """
    hn, an = home["name"], away["name"]
    hs, as_ = home["score"], away["score"]
    hp, ap = home.get("pens"), away.get("pens")
    pens = hp is not None and ap is not None
    aet = pens or "AET" in detail.upper() or detail.upper() == "ET"
    lead = "Full time (AET)" if aet else "Full time"
    text = f"{lead} - {hn} {hs}–{as_} {an}"
    if pens:
        text += f" - {hp}–{ap} penalties"
    return f"{text} ({round_name})"


def _int(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def final_signals(start_iso: str | None = None) -> list[Signal]:
    """One Signal per knockout match that has gone final (and is on/after the
    configured start). Dedup key is the ESPN event id, so each result posts once."""
    start = _parse_iso(start_iso) if start_iso else None
    try:
        resp = requests.get(SCOREBOARD, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        resp.raise_for_status()
        events = resp.json().get("events", [])
    except (requests.RequestException, ValueError):
        return []

    signals: list[Signal] = []
    for ev in events:
        round_name = KNOCKOUT_ROUNDS.get((ev.get("season") or {}).get("slug", ""))
        if not round_name:
            continue  # group stage / not a knockout -> never posted
        when = _parse_iso(ev.get("date", ""))
        if start and when and when < start:
            continue
        comp = (ev.get("competitions") or [{}])[0]
        status = (comp.get("status") or {}).get("type") or {}
        if not status.get("completed"):
            continue  # not final yet

        sides = {}
        for c in comp.get("competitors", []):
            sides[c.get("homeAway")] = {
                "name": (c.get("team") or {}).get("displayName") or "?",
                "score": _int(c.get("score")),
                "pens": _int(c.get("shootoutScore")),
            }
        home, away = sides.get("home"), sides.get("away")
        if not home or not away or home["score"] is None or away["score"] is None:
            continue

        text = _score_text(home, away, round_name, status.get("detail", ""))
        signals.append(
            Signal(
                category="worldcup",
                severity=90,
                text=text,
                dedup_key=f"wc:{ev.get('id')}",
                tz=None,  # global event -> UTC stamp
                topic="worldcup",
            )
        )
    return signals
