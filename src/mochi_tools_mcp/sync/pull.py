from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mochi_tools_mcp.sync.mapping import Mapping, save_mapping
from mochi_tools_mcp.sync.push import _hash_basis

MEDIA_RE = re.compile(r"@media/([^)\s]+)")
SPLIT_RE = re.compile(r"(?m)^---\s*\n\s*\n")


def _extract_tags(card: dict[str, Any]) -> list[str]:
    # Mochi returns server-side tags merged in `tags`; user-supplied subset in `manual-tags`.
    # Prefer manual-tags if present; otherwise fall back to tags.
    raw = card.get("manual-tags") or card.get("tags") or []
    return [str(t) for t in raw]


def _split_front_back(content: str) -> tuple[str, str]:
    parts = SPLIT_RE.split(content, maxsplit=1)
    if len(parts) != 2:
        return content, ""
    return parts[0].rstrip(), parts[1].rstrip()


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
            tags = _extract_tags(card)
            local_body = content
            if tags:
                local_body += "\n\nTags: " + " ".join(f"#{t}" for t in tags)
            name = f"card-{index:03d}.md"
            (folder / name).write_text(local_body + "\n", encoding="utf-8")
            front, back = _split_front_back(content)
            mapping.cards[name] = {"id": card["id"], "content_hash": _hash_basis(front, back, tags)}
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
