"""Local dedup + rate-limit state.

The X free / pay-per-use tier gives no read access, so we cannot ask X
whether a signal was already posted. We track it ourselves in state.json,
which the GitHub Actions workflow commits back to the repo each run.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import STATE_PATH


def _now() -> datetime:
    return datetime.now(timezone.utc)


class State:
    def __init__(self, path: Path = STATE_PATH):
        self.path = path
        self._data = {"posted": {}, "daily": {}, "monthly": {}, "daily_cat": {}}
        if path.exists():
            try:
                self._data = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        self._data.setdefault("posted", {})
        self._data.setdefault("daily", {})
        self._data.setdefault("monthly", {})
        self._data.setdefault("daily_cat", {})  # {date: {category: count}}
        self._data.setdefault("last_topic", "")  # topic of the most recent post

    # --- dedup ---------------------------------------------------------
    def already_posted(self, key: str, ttl_hours: int) -> bool:
        ts = self._data["posted"].get(key)
        if not ts:
            return False
        when = datetime.fromisoformat(ts)
        return _now() - when < timedelta(hours=ttl_hours)

    def mark_posted(self, key: str) -> None:
        self._data["posted"][key] = _now().isoformat()

    # --- last posted topic (avoid same subject back-to-back) -----------
    def last_topic(self) -> str:
        return self._data.get("last_topic", "")

    def set_last_topic(self, topic: str) -> None:
        self._data["last_topic"] = topic or ""

    # --- daily + monthly counters -------------------------------------
    def posts_today(self) -> int:
        return self._data["daily"].get(_now().date().isoformat(), 0)

    def posts_this_month(self) -> int:
        return self._data["monthly"].get(_now().strftime("%Y-%m"), 0)

    def posts_today_in(self, category: str) -> int:
        """How many posts of this category have gone out today."""
        return self._data["daily_cat"].get(_now().date().isoformat(), {}).get(category, 0)

    def increment_today(self, category: str | None = None) -> None:
        day = _now().date().isoformat()
        self._data["daily"][day] = self._data["daily"].get(day, 0) + 1
        month = _now().strftime("%Y-%m")
        self._data["monthly"][month] = self._data["monthly"].get(month, 0) + 1
        if category:
            cats = self._data["daily_cat"].setdefault(day, {})
            cats[category] = cats.get(category, 0) + 1

    # --- persistence ---------------------------------------------------
    def prune(self, ttl_hours: int) -> None:
        cutoff = _now() - timedelta(hours=ttl_hours * 4)
        self._data["posted"] = {
            k: v
            for k, v in self._data["posted"].items()
            if datetime.fromisoformat(v) > cutoff
        }
        keep = {(_now().date() - timedelta(days=d)).isoformat() for d in range(3)}
        self._data["daily"] = {
            k: v for k, v in self._data["daily"].items() if k in keep
        }
        self._data["daily_cat"] = {
            k: v for k, v in self._data["daily_cat"].items() if k in keep
        }
        # Keep this month and last month so the monthly cap survives the rollover.
        months = {_now().strftime("%Y-%m"), (_now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")}
        self._data["monthly"] = {
            k: v for k, v in self._data["monthly"].items() if k in months
        }

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2, sort_keys=True))
