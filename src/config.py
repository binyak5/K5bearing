"""Load runtime configuration and environment credentials."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
STATE_PATH = ROOT / "state.json"
# Separate state for the fast World Cup scores workflow, so it never races the
# main posting pipeline on state.json.
WC_STATE_PATH = ROOT / "wc_state.json"

USER_AGENT = "K5Bearing/1.0 (Kastle Five Systems; +https://x.com/K5Bearing)"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def x_credentials() -> dict:
    """Read X API credentials from the environment.

    Posting requires OAuth 1.0a user-context keys (consumer + access token).
    """
    return {
        "api_key": os.environ.get("X_API_KEY"),
        "api_secret": os.environ.get("X_API_SECRET"),
        "access_token": os.environ.get("X_ACCESS_TOKEN"),
        "access_token_secret": os.environ.get("X_ACCESS_TOKEN_SECRET"),
    }


def is_dry_run() -> bool:
    return os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
