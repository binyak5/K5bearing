"""Entrypoint for the fast World Cup scores workflow.

Posts knockout final scores the moment they go final, on its own ~5-minute
cadence with an isolated state file (wc_state.json), so it never races the main
30-minute posting pipeline. Run: `python -m src.worldcup` (DRY_RUN=1 to preview).
"""
from __future__ import annotations

from datetime import datetime, timezone

from .config import load_config, WC_STATE_PATH
from .state import State
from .poster import Poster
from .sources import worldcup

# A result must never re-post, so keep dedup entries well beyond the tournament.
TTL_HOURS = 24 * 60  # 60 days


def main() -> None:
    cfg = load_config().get("world_cup", {})
    if not cfg.get("enabled"):
        print("world cup scores disabled.")
        return

    start = cfg.get("start")
    if start:
        try:
            if datetime.now(timezone.utc) < datetime.fromisoformat(start.replace("Z", "+00:00")):
                print(f"before world cup start ({start}); nothing to do.")
                return
        except ValueError:
            pass

    state = State(path=WC_STATE_PATH)
    poster = Poster()
    posted = 0
    # Post every finished-but-unposted knockout result this run (not capped at
    # one) so simultaneous finals all go out promptly.
    for sig in worldcup.final_signals(start):
        if state.already_posted(sig.dedup_key, TTL_HOURS):
            continue
        if poster.post(sig.text):
            state.mark_posted(sig.dedup_key)
            posted += 1

    if posted == 0:
        print("no new world cup finals.")
    if not poster.dry_run:
        state.prune(TTL_HOURS)
        state.save()


if __name__ == "__main__":
    main()
