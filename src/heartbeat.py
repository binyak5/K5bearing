"""Operator heartbeat: DM if K5Bearing looks unhealthy.

Run on a daily schedule. Two independent checks:
  1. Has the posting workflow actually run recently? Catches a dead trigger
     (cron-job.org down, Actions disabled, repo issue).
  2. Has anything posted recently? Catches a stuck pipeline where the workflow
     runs but never posts (dead source feeds or expired X credentials).
If either looks wrong, send one alert via notify.send(); otherwise stay silent.

Run:  python -m src.heartbeat
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import requests

from . import notify
from .config import STATE_PATH

# How stale each signal can get before it's a problem. The poster runs every
# ~20 min, so a 3h gap in runs means the trigger is down. Posts are tolerated
# longer (36h) since genuinely quiet stretches happen.
RUN_STALE_HOURS = float(os.environ.get("HEARTBEAT_RUN_STALE_HOURS", "3"))
POST_STALE_HOURS = float(os.environ.get("HEARTBEAT_POST_STALE_HOURS", "36"))
TIMEOUT = 20


def _hours_since(dt: datetime) -> float:
    return (datetime.now(timezone.utc) - dt).total_seconds() / 3600


def last_post_time() -> datetime | None:
    """Most recent post timestamp recorded in state.json."""
    try:
        data = json.loads(STATE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    stamps = []
    for v in data.get("posted", {}).values():
        try:
            stamps.append(datetime.fromisoformat(v))
        except (ValueError, TypeError):
            continue
    return max(stamps) if stamps else None


def last_run_time() -> datetime | None:
    """When the posting workflow most recently ran, via the GitHub API.

    Returns None if it can't be determined, so an API hiccup never false-alarms.
    """
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        return None
    url = f"https://api.github.com/repos/{repo}/actions/workflows/post.yml/runs"
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            params={"per_page": 1},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        runs = resp.json().get("workflow_runs", [])
        if not runs:
            return None
        return datetime.fromisoformat(runs[0]["created_at"].replace("Z", "+00:00"))
    except (requests.RequestException, ValueError, KeyError):
        return None


def main() -> None:
    problems: list[str] = []

    run_dt = last_run_time()
    if run_dt is not None and _hours_since(run_dt) > RUN_STALE_HOURS:
        problems.append(
            f"the posting workflow has not run in {_hours_since(run_dt):.0f}h "
            f"(last run {run_dt:%Y-%m-%d %H:%M} UTC). The trigger may be down."
        )

    post_dt = last_post_time()
    if post_dt is None:
        problems.append("no record of any post in state.json.")
    elif _hours_since(post_dt) > POST_STALE_HOURS:
        problems.append(
            f"nothing has posted in {_hours_since(post_dt):.0f}h "
            f"(last post {post_dt:%Y-%m-%d %H:%M} UTC). Sources or X credentials may be failing."
        )

    if problems:
        msg = "K5Bearing health alert:\n- " + "\n- ".join(problems)
        notify.send(msg)
        print(msg)
    else:
        print("K5Bearing healthy.")


if __name__ == "__main__":
    main()
