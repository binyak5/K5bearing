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
            # v1.1 API is still required for media upload (v2 has no upload route).
            auth = tweepy.OAuth1UserHandler(
                creds["api_key"], creds["api_secret"],
                creds["access_token"], creds["access_token_secret"],
            )
            self._api = tweepy.API(auth)

    def post(self, text: str, image_path: str | None = None) -> bool:
        if self.dry_run:
            print("--- DRY RUN (not posted) ---")
            print(text)
            print(f"[{len(text)} chars]" + (f" + media: {image_path}" if image_path else ""))
            return True
        try:
            media_ids = None
            if image_path:
                try:
                    media = self._api.media_upload(image_path)
                    media_ids = [media.media_id_string]
                except tweepy.TweepyException as exc:
                    # Never let a card-render/upload hiccup block the post itself.
                    print(f"media upload failed, posting text-only: {exc}", file=sys.stderr)
            resp = self._client.create_tweet(text=text, media_ids=media_ids)
            tweet_id = resp.data.get("id") if resp and resp.data else "?"
            print(f"posted: https://x.com/i/web/status/{tweet_id}")
            return True
        except tweepy.TweepyException as exc:
            print(f"post failed: {exc}", file=sys.stderr)
            return False
