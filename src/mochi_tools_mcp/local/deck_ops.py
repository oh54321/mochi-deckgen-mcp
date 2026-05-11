from __future__ import annotations

import datetime as _dt
import json
import shutil
from pathlib import Path
from typing import Any

from mochi_tools_mcp.local.deck_fs import read_card as _read_card_file

CARD_PAT = "card-{i:03d}.md"


def _decks_root(root: Path) -> Path:
    return Path(root)


def _raw(root: Path) -> Path:
    return _decks_root(root) / "raw"


def _trash(root: Path) -> Path:
    return _decks_root(root) / ".trash"


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat().replace("+00:00", "Z")


def create_deck(
    root: Path, name: str, description: str = "", parent_name: str | None = None
) -> dict[str, Any]:
    folder = _raw(root) / name
    if folder.exists():
        raise FileExistsError(f"Deck {name} already exists at {folder}")
    folder.mkdir(parents=True)
    meta = {
        "name": name,
        "description": description,
        "parent_name": parent_name,
        "created_at": _now(),
    }
    (folder / "deck.json").write_text(json.dumps(meta, indent=2))
    return meta


def write_card(
    root: Path,
    deck: str,
    index: int,
    front_md: str,
    back_md: str,
    tags: list[str] | None = None,
    image_filename: str | None = None,
) -> str:
    folder = _raw(root) / deck
    if not folder.exists():
        raise FileNotFoundError(f"Deck {deck} does not exist")
    body = front_md
    if image_filename and f"]({image_filename})" not in body:
        body = f"![]({image_filename})\n\n{body}"
    body += f"\n\n---\n\n{back_md}"
    if tags:
        body += "\n\nTags: " + " ".join(f"#{t}" for t in tags)
    body += "\n"
    p = folder / CARD_PAT.format(i=index)
    p.write_text(body, encoding="utf-8")
    return str(p)


def read_card(root: Path, deck: str, index: int) -> dict[str, Any]:
    p = _raw(root) / deck / CARD_PAT.format(i=index)
    c = _read_card_file(p)
    return {
        "front_md": c.front_md,
        "back_md": c.back_md,
        "tags": c.tags,
        "image_paths": [str(x) for x in c.image_paths],
        "path": str(p),
    }


def list_decks(root: Path) -> list[dict[str, Any]]:
    raw = _raw(root)
    if not raw.exists():
        return []
    result = []
    for folder in sorted(p for p in raw.iterdir() if p.is_dir()):
        cards = list(folder.glob("card-*.md"))
        has_map = (folder / ".mochi.json").exists()
        result.append({"name": folder.name, "card_count": len(cards), "has_mochi_mapping": has_map})
    return result


def list_cards(root: Path, deck: str) -> list[dict[str, Any]]:
    folder = _raw(root) / deck
    cards = []
    for p in sorted(folder.glob("card-*.md")):
        index = int(p.stem.split("-")[1])
        c = _read_card_file(p)
        first_line = c.front_md.splitlines()[0] if c.front_md else ""
        cards.append(
            {
                "index": index,
                "front_first_line": first_line[:80],
                "tags": c.tags,
            }
        )
    return cards


def _move_to_trash(src: Path, root: Path, sub: str) -> Path:
    trash = _trash(root) / sub / _now().replace(":", "-")
    trash.mkdir(parents=True, exist_ok=True)
    dest = trash / src.name
    shutil.move(str(src), str(dest))
    return dest


def delete_card(root: Path, deck: str, index: int) -> str:
    p = _raw(root) / deck / CARD_PAT.format(i=index)
    return str(_move_to_trash(p, root, deck))


def delete_deck(root: Path, deck: str) -> str:
    folder = _raw(root) / deck
    trash = _trash(root)
    trash.mkdir(parents=True, exist_ok=True)
    dest = trash / f"{deck}-{_now().replace(':', '-')}"
    shutil.move(str(folder), str(dest))
    return str(dest)
