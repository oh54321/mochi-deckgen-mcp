from __future__ import annotations

import base64
import datetime as _dt
from collections.abc import Callable
from typing import Any

from deckgen_mcp.config import mochi_api_key
from deckgen_mcp.mochi.client import MochiClient

_AUTH_HELP = (
    "MOCHI_API_KEY missing. Get a key at https://app.mochi.cards/ → click your avatar → "
    "Account Settings → API Keys, then set MOCHI_API_KEY in your MCP client config."
)


def _err(msg: str) -> dict[str, Any]:
    return {"isError": True, "content": [{"type": "text", "text": msg}]}


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat().replace("+00:00", "Z")


def _t(name: str, fn: Callable[..., Any], description: str) -> dict[str, Any]:
    return {"name": name, "fn": fn, "description": description}


def collect() -> list[dict[str, Any]]:
    def _client_or_err() -> MochiClient | dict[str, Any]:
        key = mochi_api_key()
        if not key:
            return _err(_AUTH_HELP)
        return MochiClient(api_key=key)

    def wrap(method_name: str) -> Callable[..., Any]:
        def runner(**kwargs: Any) -> Any:
            c = _client_or_err()
            if isinstance(c, dict):
                return c
            return getattr(c, method_name)(**kwargs)

        return runner

    def mochi_trash_deck(deck_id: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.trash_deck(deck_id, _now())

    def mochi_trash_card(card_id: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.trash_card(card_id, _now())

    def mochi_add_attachment(
        card_id: str, filename: str, base64_content: str, content_type: str
    ) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.add_attachment(card_id, filename, base64.b64decode(base64_content), content_type)

    return [
        _t("mochi_list_decks", wrap("list_decks"), "List Mochi decks."),
        _t("mochi_get_deck", wrap("get_deck"), "Get a Mochi deck by id."),
        _t("mochi_create_deck", wrap("create_deck"), "Create a Mochi deck."),
        _t("mochi_update_deck", wrap("update_deck"), "Update a Mochi deck."),
        _t("mochi_delete_deck", wrap("delete_deck"), "Hard-delete a Mochi deck."),
        _t("mochi_trash_deck", mochi_trash_deck, "Soft-delete (trash) a Mochi deck."),
        _t("mochi_list_cards", wrap("list_cards"), "List Mochi cards."),
        _t("mochi_get_card", wrap("get_card"), "Get a Mochi card by id."),
        _t("mochi_create_card", wrap("create_card"), "Create a Mochi card."),
        _t("mochi_update_card", wrap("update_card"), "Update a Mochi card."),
        _t("mochi_delete_card", wrap("delete_card"), "Hard-delete a Mochi card."),
        _t("mochi_trash_card", mochi_trash_card, "Soft-delete (trash) a Mochi card."),
        _t(
            "mochi_add_attachment",
            mochi_add_attachment,
            "Add an attachment to a Mochi card (base64).",
        ),
        _t("mochi_delete_attachment", wrap("delete_attachment"), "Delete an attachment."),
        _t("mochi_list_templates", wrap("list_templates"), "List Mochi templates."),
        _t("mochi_get_template", wrap("get_template"), "Get a Mochi template by id."),
        _t("mochi_create_template", wrap("create_template"), "Create a Mochi template."),
        _t(
            "mochi_get_due_cards",
            wrap("get_due_cards"),
            "Get due cards (optionally for one deck).",
        ),
    ]
