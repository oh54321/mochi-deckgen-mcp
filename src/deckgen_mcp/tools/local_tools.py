from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from deckgen_mcp.config import decks_root
from deckgen_mcp.local import deck_ops, image_fetch, image_import, image_wikipedia, malformed_check


def _t(name: str, fn: Callable[..., Any], description: str) -> dict[str, Any]:
    return {"name": name, "fn": fn, "description": description}


def collect() -> list[dict[str, Any]]:
    root = decks_root

    def local_create_deck(
        name: str, description: str = "", parent_name: str | None = None
    ) -> dict[str, Any]:
        return deck_ops.create_deck(root(), name, description, parent_name)

    def local_write_card(
        deck: str,
        index: int,
        front_md: str,
        back_md: str,
        tags: list[str] | None = None,
        image_filename: str | None = None,
    ) -> dict[str, Any]:
        path = deck_ops.write_card(root(), deck, index, front_md, back_md, tags, image_filename)
        return {"path": path}

    def local_read_card(deck: str, index: int) -> dict[str, Any]:
        return deck_ops.read_card(root(), deck, index)

    def local_list_decks() -> list[dict[str, Any]]:
        return deck_ops.list_decks(root())

    def local_list_cards(deck: str) -> list[dict[str, Any]]:
        return deck_ops.list_cards(root(), deck)

    def local_delete_card(deck: str, index: int) -> dict[str, Any]:
        return {"trashed_to": deck_ops.delete_card(root(), deck, index)}

    def local_delete_deck(name: str) -> dict[str, Any]:
        return {"trashed_to": deck_ops.delete_deck(root(), name)}

    def local_fetch_image(url: str, deck: str, max_edge_px: int = 1024) -> dict[str, Any]:
        dest = root() / "raw" / deck / "images"
        p = image_fetch.fetch_image(url, dest, max_edge_px)
        return {"path": str(p) if p else None}

    def local_fetch_wikipedia_image(query: str, deck: str) -> dict[str, Any] | None:
        dest = root() / "raw" / deck / "images"
        return image_wikipedia.fetch_wikipedia_image(query, dest)

    def local_import_image(
        deck: str,
        file_path: str | None = None,
        base64_data: str | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        dest = root() / "raw" / deck / "images"
        p = image_import.import_image(
            dest,
            file_path=Path(file_path) if file_path else None,
            base64_data=base64_data,
            filename=filename,
        )
        return {"path": p}

    def local_check_malformed(deck: str, index: int | None = None) -> Any:
        folder = root() / "raw" / deck
        if index is not None:
            return malformed_check.check_card_file(folder / f"card-{index:03d}.md")
        results: dict[int, Any] = {}
        for p in sorted(folder.glob("card-*.md")):
            i = int(p.stem.split("-")[1])
            results[i] = malformed_check.check_card_file(p)
        return results

    return [
        _t("local_create_deck", local_create_deck, "Create a new local deck folder."),
        _t("local_write_card", local_write_card, "Write a card to a local deck."),
        _t("local_read_card", local_read_card, "Read a card from a local deck."),
        _t("local_list_decks", local_list_decks, "List local decks."),
        _t("local_list_cards", local_list_cards, "List cards in a local deck."),
        _t("local_delete_card", local_delete_card, "Soft-delete a card (move to .trash/)."),
        _t("local_delete_deck", local_delete_deck, "Soft-delete a deck (move to .trash/)."),
        _t(
            "local_fetch_image",
            local_fetch_image,
            "Download, process, dedup an image into a deck.",
        ),
        _t(
            "local_fetch_wikipedia_image",
            local_fetch_wikipedia_image,
            "Fetch an image from Wikipedia Commons.",
        ),
        _t("local_import_image", local_import_image, "Import a user-supplied image."),
        _t("local_check_malformed", local_check_malformed, "Regex-only structural check of cards."),
    ]
