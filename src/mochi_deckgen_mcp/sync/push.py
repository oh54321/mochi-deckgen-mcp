from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

from mochi_deckgen_mcp.local.deck_fs import read_deck
from mochi_deckgen_mcp.sync.mapping import Mapping, hash_text, load_mapping, save_mapping


def _card_content_for_mochi(front_md: str, back_md: str) -> str:
    """Body sent to Mochi. Tags are NOT included — they go in manual-tags."""
    return f"{front_md}\n\n---\n\n{back_md}"


def _hash_basis(front_md: str, back_md: str, tags: list[str]) -> str:
    """Content+tags fingerprint for incremental-push diffing."""
    parts = [front_md, back_md] + sorted(tags)
    return hash_text("\n--TAG--\n".join(parts))


def _deck_folder(decks_root: Path, deck_name: str) -> Path:
    return Path(decks_root, "raw", *deck_name.split("/"))


def _resolve_parent_id(decks_root: Path, deck_name: str, mochi_client: Any) -> str | None:
    """For 'A/B/C', look up the Mochi deck_id of 'A/B'. Push it first if missing."""
    parts = deck_name.split("/")
    if len(parts) < 2:
        return None
    parent_name = "/".join(parts[:-1])
    parent_folder = _deck_folder(decks_root, parent_name)
    if not parent_folder.exists() or not (parent_folder / "deck.json").exists():
        return None
    parent_mapping = load_mapping(parent_folder)
    if parent_mapping is not None:
        return parent_mapping.deck_id
    # Recursively push the parent so it gets a Mochi id, then return that.
    push_deck(decks_root, parent_name, mochi_client)
    parent_mapping = load_mapping(parent_folder)
    return parent_mapping.deck_id if parent_mapping else None


def push_deck(
    decks_root: Path, deck_name: str, mochi_client: Any, parent_id: str | None = None
) -> dict[str, Any]:
    folder = _deck_folder(Path(decks_root), deck_name)
    deck = read_deck(folder)
    mapping = load_mapping(folder)
    created = 0
    updated = 0

    if mapping is None:
        resolved_parent = parent_id or _resolve_parent_id(Path(decks_root), deck_name, mochi_client)
        # The deck name on Mochi is the leaf segment (Mochi reflects hierarchy via parent-id).
        leaf_name = deck_name.split("/")[-1]
        result = mochi_client.create_deck(name=leaf_name, parent_id=resolved_parent)
        mapping = Mapping(
            deck_id=result["id"], deck_name_on_mochi=leaf_name, parent_id=resolved_parent
        )

    for card in deck.cards:
        name = card.source_path.name if card.source_path else ""
        content = _card_content_for_mochi(card.front_md, card.back_md)
        digest = _hash_basis(card.front_md, card.back_md, card.tags)
        prev = mapping.cards.get(name)
        if prev is None:
            r = mochi_client.create_card(
                deck_id=mapping.deck_id, content=content, manual_tags=card.tags or None
            )
            mapping.cards[name] = {"id": r["id"], "content_hash": digest}
            created += 1
        elif prev["content_hash"] != digest:
            mochi_client.update_card(prev["id"], content=content, manual_tags=card.tags or None)
            mapping.cards[name] = {"id": prev["id"], "content_hash": digest}
            updated += 1

    mapping.last_push_at = _dt.datetime.now(_dt.UTC).isoformat().replace("+00:00", "Z")
    save_mapping(folder, mapping)
    return {"deck_id": mapping.deck_id, "created": created, "updated": updated}


# Backwards-compat shim used by sync/diff.py
def _card_content(front_md: str, back_md: str, tags: list[str]) -> str:
    return _card_content_for_mochi(front_md, back_md)
