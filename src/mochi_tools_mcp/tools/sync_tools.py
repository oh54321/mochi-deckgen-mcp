from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from mochi_tools_mcp.config import decks_root, mochi_api_key
from mochi_tools_mcp.mochi.client import MochiClient
from mochi_tools_mcp.sync.diff import sync_status
from mochi_tools_mcp.sync.mapping import Mapping, save_mapping
from mochi_tools_mcp.sync.pull import pull_deck
from mochi_tools_mcp.sync.push import push_deck

_AUTH_HELP = (
    "MOCHI_API_KEY missing. Get a key at https://app.mochi.cards/ → click your avatar → "
    "Account Settings → API Keys, then set MOCHI_API_KEY in your MCP client config."
)


def _err(msg: str) -> dict[str, Any]:
    return {"isError": True, "content": [{"type": "text", "text": msg}]}


def _t(name: str, fn: Callable[..., Any], description: str) -> dict[str, Any]:
    return {"name": name, "fn": fn, "description": description}


def collect() -> list[dict[str, Any]]:
    def _c() -> MochiClient | None:
        k = mochi_api_key()
        return MochiClient(api_key=k) if k else None

    def sync_push_deck(deck: str, parent_id: str | None = None) -> Any:
        c = _c()
        if c is None:
            return _err(_AUTH_HELP)
        return push_deck(decks_root(), deck, c, parent_id=parent_id)

    def sync_pull_deck(deck_id: str) -> Any:
        c = _c()
        if c is None:
            return _err(_AUTH_HELP)
        return pull_deck(decks_root(), deck_id, c)

    def sync_status_tool(deck: str) -> Any:
        c = _c()
        if c is None:
            return _err(_AUTH_HELP)
        return sync_status(decks_root(), deck, c)

    def sync_link(deck: str, deck_id: str, deck_name_on_mochi: str | None = None) -> dict[str, Any]:
        folder = Path(decks_root(), "raw", *deck.split("/"))
        m = Mapping(deck_id=deck_id, deck_name_on_mochi=deck_name_on_mochi or deck)
        save_mapping(folder, m)
        return {"linked": str(folder), "deck_id": deck_id}

    return [
        _t("sync_push_deck", sync_push_deck, "Push local deck to Mochi (incremental)."),
        _t("sync_pull_deck", sync_pull_deck, "Pull a Mochi deck into local markdown."),
        _t("sync_status", sync_status_tool, "Compare local vs Mochi for a deck."),
        _t("sync_link", sync_link, "Associate a local folder with a Mochi deck id."),
    ]
