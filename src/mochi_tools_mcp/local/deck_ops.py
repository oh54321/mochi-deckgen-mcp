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


def _deck_folder(root: Path, name: str) -> Path:
    """Resolve a deck name (possibly containing slashes) to its folder."""
    return _raw(root).joinpath(*name.split("/"))


def create_deck(
    root: Path, name: str, description: str = "", parent_name: str | None = None
) -> dict[str, Any]:
    """Create a deck. `name` may contain slashes for nesting (e.g. 'Languages/Spanish').

    Any path segments that don't yet have a deck.json get auto-promoted to empty
    decks so the Mochi hierarchy will mirror the local folder structure on push.
    """
    folder = _deck_folder(root, name)
    if folder.exists() and (folder / "deck.json").exists():
        raise FileExistsError(f"Deck {name} already exists at {folder}")

    # Auto-create each ancestor that lacks deck.json (without overwriting any that exist).
    parts = name.split("/")
    for i in range(1, len(parts)):
        ancestor = "/".join(parts[:i])
        ancestor_folder = _deck_folder(root, ancestor)
        if (ancestor_folder / "deck.json").exists():
            continue
        ancestor_folder.mkdir(parents=True, exist_ok=True)
        ancestor_parent = "/".join(parts[: i - 1]) or None
        (ancestor_folder / "deck.json").write_text(
            json.dumps(
                {
                    "name": ancestor,
                    "description": "",
                    "parent_name": ancestor_parent,
                    "created_at": _now(),
                },
                indent=2,
            )
        )

    folder.mkdir(parents=True, exist_ok=True)
    parent_from_path = "/".join(parts[:-1]) or None
    meta = {
        "name": name,
        "description": description,
        "parent_name": parent_name or parent_from_path,
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
    folder = _deck_folder(root, deck)
    if not (folder / "deck.json").exists():
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
    p = _deck_folder(root, deck) / CARD_PAT.format(i=index)
    c = _read_card_file(p)
    return {
        "front_md": c.front_md,
        "back_md": c.back_md,
        "tags": c.tags,
        "image_paths": [str(x) for x in c.image_paths],
        "path": str(p),
    }


def list_decks(root: Path) -> list[dict[str, Any]]:
    """Walk the raw/ tree and return every directory with a deck.json.

    Names are slash-joined relative to raw/ (e.g. 'Languages/Spanish').
    Result is sorted depth-first so parents appear before children.
    """
    raw = _raw(root)
    if not raw.exists():
        return []
    result = []
    for deck_json in sorted(raw.rglob("deck.json")):
        folder = deck_json.parent
        relative = folder.relative_to(raw)
        name = "/".join(relative.parts)
        cards = list(folder.glob("card-*.md"))
        has_map = (folder / ".mochi.json").exists()
        parent_name = "/".join(name.split("/")[:-1]) or None
        result.append(
            {
                "name": name,
                "card_count": len(cards),
                "has_mochi_mapping": has_map,
                "parent_name": parent_name,
                "depth": len(name.split("/")) - 1,
            }
        )
    return result


def list_cards(root: Path, deck: str) -> list[dict[str, Any]]:
    folder = _deck_folder(root, deck)
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
    trash = _trash(root) / sub.replace("/", "__") / _now().replace(":", "-")
    trash.mkdir(parents=True, exist_ok=True)
    dest = trash / src.name
    shutil.move(str(src), str(dest))
    return dest


def delete_card(root: Path, deck: str, index: int) -> str:
    p = _deck_folder(root, deck) / CARD_PAT.format(i=index)
    return str(_move_to_trash(p, root, deck))


def delete_deck(root: Path, deck: str) -> str:
    folder = _deck_folder(root, deck)
    trash = _trash(root)
    trash.mkdir(parents=True, exist_ok=True)
    safe = deck.replace("/", "__")
    dest = trash / f"{safe}-{_now().replace(':', '-')}"
    shutil.move(str(folder), str(dest))
    return str(dest)
