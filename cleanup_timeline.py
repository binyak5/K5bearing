#!/usr/bin/env python3
"""One-off: delete every NON-Rotterdam tweet from the K5Bearing timeline.

KEEP rule: the tweet text contains "rotterdam" (case-insensitive) -> it's a
Rotterdam weather post (the routine twice-daily forecast, which starts with
"Rotterdam", or a Rotterdam thunderstorm alert, tagged "EU, Rotterdam").
Everything else (Gulf, US, other-EU, marine, space weather, World Cup) is
deleted.

This is DESTRUCTIVE and IRREVERSIBLE. It runs a dry run by default: it prints
what it would keep vs delete and writes a full manifest, but changes nothing.
Only `--execute` actually deletes.

Run from the repo root, with the live X credentials exported in your shell
(they normally live only in GitHub secrets):

    export X_API_KEY=...  X_API_SECRET=...  X_ACCESS_TOKEN=...  X_ACCESS_TOKEN_SECRET=...
    python cleanup_timeline.py            # dry run — no changes
    python cleanup_timeline.py --execute  # actually delete the DELETE set

Note: the timeline read endpoint reaches only the ~3200 most recent tweets and
consumes your API read quota; deletes use a separate write quota.
"""
from __future__ import annotations

import sys

import tweepy

from src.config import x_credentials

# A tweet is kept iff its text contains this (lowercased). Both the routine
# Rotterdam forecast and Rotterdam thunderstorm alerts contain "Rotterdam";
# no other source on the feed does.
KEEP_SUBSTR = "rotterdam"


def build_client() -> tweepy.Client:
    creds = x_credentials()
    missing = [k for k, v in creds.items() if not v]
    if missing:
        sys.exit(
            "Missing X credentials: " + ", ".join(missing) + ".\n"
            "Export them in your shell before running (see the module docstring)."
        )
    return tweepy.Client(
        consumer_key=creds["api_key"],
        consumer_secret=creds["api_secret"],
        access_token=creds["access_token"],
        access_token_secret=creds["access_token_secret"],
        wait_on_rate_limit=True,  # sleep through 429s rather than crash
    )


def fetch_all(client: tweepy.Client, user_id) -> list:
    """Every original tweet on the account (no replies/retweets), newest first."""
    tweets: list = []
    for page in tweepy.Paginator(
        client.get_users_tweets,
        id=user_id,
        max_results=100,
        exclude=["retweets", "replies"],
        tweet_fields=["created_at"],
    ):
        if page.data:
            tweets.extend(page.data)
    return tweets


def is_rotterdam(text: str) -> bool:
    return KEEP_SUBSTR in (text or "").lower()


def _one_line(text: str, n: int = 90) -> str:
    return " ".join((text or "").split())[:n]


def _read_blocked(exc: Exception) -> None:
    """Explain a failed read (the common case: the X access tier has no read
    scope), then exit non-zero."""
    print("\n" + "=" * 60, file=sys.stderr)
    print("READ FAILED. This step needs to READ your timeline before it can", file=sys.stderr)
    print("delete anything, and that read was rejected:", file=sys.stderr)
    print(f"  {type(exc).__name__}: {exc}", file=sys.stderr)
    print("", file=sys.stderr)
    if isinstance(exc, tweepy.Forbidden):
        print("A 403/Forbidden here almost always means your X API access tier", file=sys.stderr)
        print("does not allow reading tweets (many pay-per-use / free tiers are", file=sys.stderr)
        print("write-only). The bot can still POST, but not enumerate the", file=sys.stderr)
        print("timeline to find what to delete.", file=sys.stderr)
        print("Options: (a) raise the app's access tier so reads are allowed,", file=sys.stderr)
        print("or (b) delete manually / with a third-party tool instead.", file=sys.stderr)
    elif isinstance(exc, tweepy.TooManyRequests):
        print("A 429/TooManyRequests means the read quota is exhausted for now.", file=sys.stderr)
        print("Wait for the window to reset and try the dry run again.", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    sys.exit(1)


def main() -> None:
    execute = "--execute" in sys.argv
    client = build_client()

    try:
        me = client.get_me()
    except tweepy.TweepyException as exc:
        _read_blocked(exc)
    if not me or not me.data:
        sys.exit("Could not resolve the authenticated account (get_me returned no data).")
    uid, handle = me.data.id, me.data.username
    print(f"Account: @{handle} (id {uid})")

    try:
        tweets = fetch_all(client, uid)
    except tweepy.TweepyException as exc:
        _read_blocked(exc)
    print(f"Fetched {len(tweets)} original tweets (endpoint reaches ~3200 most recent).")
    if not tweets:
        print("Nothing to do.")
        return

    keep = [t for t in tweets if is_rotterdam(t.text)]
    delete = [t for t in tweets if not is_rotterdam(t.text)]
    print(f"KEEP (Rotterdam): {len(keep)}    DELETE (non-Rotterdam): {len(delete)}")

    print("\n--- sample KEEP (first 5) ---")
    for t in keep[:5]:
        print("  KEEP  ", _one_line(t.text))
    print("\n--- sample DELETE (first 12) ---")
    for t in delete[:12]:
        print("  DEL   ", _one_line(t.text))

    with open("cleanup_manifest.txt", "w", encoding="utf-8") as fh:
        for t in delete:
            fh.write(f"DELETE\t{t.id}\t{_one_line(t.text, 300)}\n")
        for t in keep:
            fh.write(f"KEEP\t{t.id}\t{_one_line(t.text, 300)}\n")
    print("\nFull manifest written to cleanup_manifest.txt (also uploaded as a workflow artifact).")

    if not execute:
        # Print the whole delete list to the log so it can be reviewed inline,
        # no download needed, before anyone runs the execute pass.
        print(f"\n=== FULL DELETE LIST ({len(delete)} tweets) ===")
        for t in delete:
            print("  DEL   ", _one_line(t.text, 120))
        print("\nDRY RUN — nothing was deleted. Re-run with confirm=DELETE to delete the list above.")
        return

    print(f"\nEXECUTING: deleting {len(delete)} non-Rotterdam tweets (irreversible)...")
    ok = fail = 0
    for t in delete:
        try:
            client.delete_tweet(t.id)
            ok += 1
            if ok % 20 == 0:
                print(f"  ...deleted {ok}")
        except tweepy.TweepyException as exc:
            fail += 1
            print(f"  FAILED {t.id}: {exc}", file=sys.stderr)
    print(f"Done. deleted={ok} failed={fail} kept={len(keep)}")


if __name__ == "__main__":
    main()
