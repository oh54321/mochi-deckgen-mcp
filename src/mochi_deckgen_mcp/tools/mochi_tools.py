from __future__ import annotations

import base64
import datetime as _dt
from collections.abc import Callable
from typing import Any

from mochi_deckgen_mcp.config import mochi_api_key
from mochi_deckgen_mcp.mochi.client import MochiClient

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


def _client_or_err() -> MochiClient | dict[str, Any]:
    key = mochi_api_key()
    if not key:
        return _err(_AUTH_HELP)
    return MochiClient(api_key=key)


def collect() -> list[dict[str, Any]]:
    def mochi_list_decks(bookmark: str | None = None) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.list_decks(bookmark=bookmark)

    def mochi_get_deck(deck_id: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.get_deck(deck_id)

    def mochi_create_deck(
        name: str,
        parent_id: str | None = None,
        sort: int | None = None,
        archived: bool | None = None,
        sort_by: str | None = None,
        cards_view: str | None = None,
        show_sides: bool | None = None,
        sort_by_direction: bool | None = None,
        review_reverse: bool | None = None,
    ) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.create_deck(
            name,
            parent_id=parent_id,
            sort=sort,
            archived=archived,
            sort_by=sort_by,
            cards_view=cards_view,
            show_sides=show_sides,
            sort_by_direction=sort_by_direction,
            review_reverse=review_reverse,
        )

    def mochi_update_deck(
        deck_id: str,
        name: str | None = None,
        parent_id: str | None = None,
        sort: int | None = None,
        archived: bool | None = None,
        sort_by: str | None = None,
        cards_view: str | None = None,
        show_sides: bool | None = None,
        sort_by_direction: bool | None = None,
        review_reverse: bool | None = None,
    ) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        fields: dict[str, Any] = {}
        if name is not None:
            fields["name"] = name
        if parent_id is not None:
            fields["parent-id"] = parent_id
        if sort is not None:
            fields["sort"] = sort
        if archived is not None:
            fields["archived?"] = archived
        if sort_by is not None:
            fields["sort-by"] = sort_by
        if cards_view is not None:
            fields["cards-view"] = cards_view
        if show_sides is not None:
            fields["show-sides?"] = show_sides
        if sort_by_direction is not None:
            fields["sort-by-direction"] = sort_by_direction
        if review_reverse is not None:
            fields["review-reverse?"] = review_reverse
        return c.update_deck(deck_id, **fields)

    def mochi_delete_deck(deck_id: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.delete_deck(deck_id)

    def mochi_trash_deck(deck_id: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.trash_deck(deck_id, _now())

    def mochi_list_cards(deck_id: str | None = None, bookmark: str | None = None) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.list_cards(deck_id=deck_id, bookmark=bookmark)

    def mochi_get_card(card_id: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.get_card(card_id)

    def mochi_create_card(
        deck_id: str,
        content: str,
        template_id: str | None = None,
        fields: dict[str, Any] | None = None,
        manual_tags: list[str] | None = None,
        archived: bool | None = None,
        review_reverse: bool | None = None,
        pos: str | None = None,
    ) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.create_card(
            deck_id=deck_id,
            content=content,
            template_id=template_id,
            fields=fields,
            manual_tags=manual_tags,
            archived=archived,
            review_reverse=review_reverse,
            pos=pos,
        )

    def mochi_update_card(
        card_id: str,
        content: str | None = None,
        deck_id: str | None = None,
        fields: dict[str, Any] | None = None,
        manual_tags: list[str] | None = None,
        archived: bool | None = None,
        review_reverse: bool | None = None,
        pos: str | None = None,
    ) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        body: dict[str, Any] = {}
        if content is not None:
            body["content"] = content
        if deck_id is not None:
            body["deck-id"] = deck_id
        if fields is not None:
            body["fields"] = fields
        if manual_tags is not None:
            body["manual-tags"] = manual_tags
        if archived is not None:
            body["archived?"] = archived
        if review_reverse is not None:
            body["review-reverse?"] = review_reverse
        if pos is not None:
            body["pos"] = pos
        return c.update_card(card_id, **body)

    def mochi_delete_card(card_id: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.delete_card(card_id)

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

    def mochi_delete_attachment(card_id: str, filename: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.delete_attachment(card_id, filename)

    def mochi_list_templates() -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.list_templates()

    def mochi_get_template(template_id: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.get_template(template_id)

    def mochi_create_template(name: str, content: str, fields: dict[str, Any] | None = None) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.create_template(name=name, content=content, fields=fields)

    def mochi_get_due_cards(deck_id: str | None = None) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.get_due_cards(deck_id=deck_id)

    return [
        _t("mochi_list_decks", mochi_list_decks, "List Mochi decks."),
        _t("mochi_get_deck", mochi_get_deck, "Get a Mochi deck by id."),
        _t("mochi_create_deck", mochi_create_deck, "Create a Mochi deck."),
        _t("mochi_update_deck", mochi_update_deck, "Update a Mochi deck (name and/or parent)."),
        _t("mochi_delete_deck", mochi_delete_deck, "Hard-delete a Mochi deck."),
        _t("mochi_trash_deck", mochi_trash_deck, "Soft-delete (trash) a Mochi deck."),
        _t("mochi_list_cards", mochi_list_cards, "List Mochi cards (optionally filtered by deck)."),
        _t("mochi_get_card", mochi_get_card, "Get a Mochi card by id."),
        _t("mochi_create_card", mochi_create_card, "Create a Mochi card."),
        _t(
            "mochi_update_card", mochi_update_card, "Update a Mochi card (content / deck / fields)."
        ),
        _t("mochi_delete_card", mochi_delete_card, "Hard-delete a Mochi card."),
        _t("mochi_trash_card", mochi_trash_card, "Soft-delete (trash) a Mochi card."),
        _t(
            "mochi_add_attachment",
            mochi_add_attachment,
            "Add an attachment to a Mochi card (base64).",
        ),
        _t(
            "mochi_delete_attachment",
            mochi_delete_attachment,
            "Delete an attachment from a Mochi card.",
        ),
        _t("mochi_list_templates", mochi_list_templates, "List Mochi templates."),
        _t("mochi_get_template", mochi_get_template, "Get a Mochi template by id."),
        _t("mochi_create_template", mochi_create_template, "Create a Mochi template."),
        _t(
            "mochi_get_due_cards",
            mochi_get_due_cards,
            "Get due cards (optionally for one deck).",
        ),
    ]
