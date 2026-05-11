from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from deckgen_mcp.sync.mapping import Mapping, hash_text, save_mapping

MEDIA_RE = re.compile(r"@media/([^)\s]+)")


def pull_deck(decks_root: Path, deck_id: str, mochi_client: Any) -> dict[str, Any]:
    deck_meta = mochi_client.get_deck(deck_id)
    folder = Path(decks_root) / "raw" / deck_meta["name"]
    folder.mkdir(parents=True, exist_ok=True)

    missing: set[str] = set()
    mapping = Mapping(deck_id=deck_id, deck_name_on_mochi=deck_meta["name"])

    index = 1
    bookmark = None
    while True:
        page = mochi_client.list_cards(deck_id=deck_id, bookmark=bookmark)
        for card in page["docs"]:
            content = card["content"]
            for m in MEDIA_RE.finditer(content):
                missing.add(m.group(1))
            content = MEDIA_RE.sub(r"images/\1", content)
            name = f"card-{index:03d}.md"
            (folder / name).write_text(content + "\n", encoding="utf-8")
            mapping.cards[name] = {"id": card["id"], "content_hash": hash_text(content)}
            index += 1
        bookmark = page.get("bookmark")
        if not bookmark:
            break

    save_mapping(folder, mapping)
    if missing:
        (folder / "attachments-not-downloaded.txt").write_text(
            "Mochi API does not expose attachment downloads. "
            "These files are referenced but not present locally:\n"
            + "\n".join(sorted(missing))
            + "\n",
            encoding="utf-8",
        )
    return {
        "deck_name": deck_meta["name"],
        "cards_pulled": index - 1,
        "missing_images": sorted(missing),
    }
