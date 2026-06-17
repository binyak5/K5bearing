"""Outbound operator notifications, via Telegram.

Used by the heartbeat to DM the operator when the bot looks unhealthy. Reads
TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from the environment; if either is
missing it logs and no-ops, so nothing breaks when notifications aren't set up.

Setup: message @BotFather to create a bot (gives the token), then message your
new bot once and read your chat id from
https://api.telegram.org/bot<TOKEN>/getUpdates. Store both as GitHub secrets.
"""
from __future__ import annotations

import os

import requests

TIMEOUT = 15


def send(text: str) -> bool:
    """DM the operator. Returns True on success, False if unconfigured/failed."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("notify: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set; skipping")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"notify: failed to send Telegram message: {e}")
        return False
