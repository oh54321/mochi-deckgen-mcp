from __future__ import annotations

import os
from pathlib import Path


def decks_root() -> Path:
    env = os.environ.get("DECKGEN_DECKS_ROOT")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".local" / "share" / "mochi-tools-mcp" / "decks"


def default_regen() -> int:
    return int(os.environ.get("DECKGEN_DEFAULT_REGEN", "1"))


def default_concurrency() -> int:
    return int(os.environ.get("DECKGEN_DEFAULT_CONCURRENCY", "10"))


def mochi_api_key() -> str | None:
    return os.environ.get("MOCHI_API_KEY")
