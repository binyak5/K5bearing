"""Post to X via the v2 API (tweepy), with a dry-run mode for testing."""
from __future__ import annotations

import sys

import tweepy

from .config import x_credentials, is_dry_run


class Poster:
    def __init__(self):
        self.dry_run = is_dry_run()
        self._client = None
        if not self.dry_run:
            creds = x_credentials()
            missing = [k for k, v in creds.items() if not v]
            if missing:
                raise RuntimeError(
                    f"Missing X credentials: {', '.join(missing)}. "
                    "Set them as env vars / GitHub secrets, or run with DRY_RUN=1."
                )
            self._client = tweepy.Client(
                consumer_key=creds["api_key"],
                consumer_secret=creds["api_secret"],
                access_token=creds["access_token"],
                access_token_secret=creds["access_token_secret"],
            )

    def post(self, text: str) -> bool:
        if self.dry_run:
            print("--- DRY RUN (not posted) ---")
            print(text)
            print(f"[{len(text)} chars]")
            return True
        try:
            resp = self._client.create_tweet(text=text)
            tweet_id = resp.data.get("id") if resp and resp.data else "?"
            print(f"posted: https://x.com/i/web/status/{tweet_id}")
            return True
        except tweepy.TweepyException as exc:
            print(f"post failed: {exc}", file=sys.stderr)
            return False
