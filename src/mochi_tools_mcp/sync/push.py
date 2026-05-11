from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

from mochi_tools_mcp.local.deck_fs import read_deck
from mochi_tools_mcp.sync.mapping import Mapping, hash_text, load_mapping, save_mapping


def _card_content(front_md: str, back_md: str, tags: list[str]) -> str:
    body = f"{front_md}\n\n---\n\n{back_md}"
    if tags:
        body += "\n\nTags: " + " ".join(f"#{t}" for t in tags)
    return body


def push_deck(
    decks_root: Path, deck_name: str, mochi_client: Any, parent_id: str | None = None
) -> dict[str, Any]:
    folder = Path(decks_root) / "raw" / deck_name
    deck = read_deck(folder)
    mapping = load_mapping(folder)
    created = 0
    updated = 0

    if mapping is None:
        result = mochi_client.create_deck(name=deck.name, parent_id=parent_id)
        mapping = Mapping(deck_id=result["id"], deck_name_on_mochi=deck.name, parent_id=parent_id)

    for card in deck.cards:
        name = card.source_path.name if card.source_path else ""
        content = _card_content(card.front_md, card.back_md, card.tags)
        digest = hash_text(content)
        prev = mapping.cards.get(name)
        if prev is None:
            r = mochi_client.create_card(deck_id=mapping.deck_id, content=content)
            mapping.cards[name] = {"id": r["id"], "content_hash": digest}
            created += 1
        elif prev["content_hash"] != digest:
            mochi_client.update_card(prev["id"], content=content)
            mapping.cards[name] = {"id": prev["id"], "content_hash": digest}
            updated += 1

    mapping.last_push_at = _dt.datetime.now(_dt.UTC).isoformat().replace("+00:00", "Z")
    save_mapping(folder, mapping)
    return {"deck_id": mapping.deck_id, "created": created, "updated": updated}
