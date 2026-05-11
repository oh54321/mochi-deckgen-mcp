from __future__ import annotations

from pathlib import Path
from typing import Any

from mochi_tools_mcp.local.deck_fs import read_deck
from mochi_tools_mcp.sync.mapping import load_mapping
from mochi_tools_mcp.sync.push import _hash_basis


def sync_status(decks_root: Path, deck_name: str, mochi_client: Any) -> list[dict[str, Any]]:
    folder = Path(decks_root, "raw", *deck_name.split("/"))
    deck = read_deck(folder)
    mapping = load_mapping(folder)
    rows: list[dict[str, Any]] = []

    local_by_name: dict[str, str] = {}
    for c in deck.cards:
        name = c.source_path.name if c.source_path else ""
        local_by_name[name] = _hash_basis(c.front_md, c.back_md, c.tags)

    remote_ids: set[str] = set()
    if mapping:
        page = mochi_client.list_cards(deck_id=mapping.deck_id)
        for card in page["docs"]:
            remote_ids.add(card["id"])

    if mapping is None:
        for name in local_by_name:
            rows.append({"name": name, "status": "new-locally"})
        return rows

    for name, h in local_by_name.items():
        prev = mapping.cards.get(name)
        if prev is None:
            rows.append({"name": name, "status": "new-locally"})
        elif prev["content_hash"] != h:
            rows.append({"name": name, "status": "changed-locally"})
        else:
            rows.append({"name": name, "status": "in-sync"})

    mapped_ids = {v["id"] for v in mapping.cards.values()}
    for rid in remote_ids - mapped_ids:
        rows.append({"name": rid, "status": "new-remotely"})
    return rows
