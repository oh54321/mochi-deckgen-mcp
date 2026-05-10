from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

TAGS_RE = re.compile(r"^Tags:\s*((?:#\S+\s*)+)$", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
SPLIT_RE = re.compile(r"(?m)^---\s*\n\s*\n")


@dataclass
class Card:
    front_md: str
    back_md: str
    tags: list[str] = field(default_factory=list)
    image_paths: list[Path] = field(default_factory=list)
    source_path: Path | None = None


def read_card(path: Path) -> Card:
    text = Path(path).read_text(encoding="utf-8")
    parts = SPLIT_RE.split(text, maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Card {path} missing front/back separator")
    front, back = parts[0].strip("\n"), parts[1].strip("\n")

    tags: list[str] = []
    m = TAGS_RE.search(back)
    if m:
        tags = [t.lstrip("#") for t in m.group(1).split()]
        back = back[: m.start()].rstrip("\n")

    images = [Path(p) for p in IMAGE_RE.findall(front + "\n" + back)]
    return Card(front_md=front, back_md=back, tags=tags, image_paths=images, source_path=Path(path))


@dataclass
class Deck:
    name: str
    description: str
    cards: list[Card]
    metadata: dict
    folder: Path


def read_deck(folder: Path) -> Deck:
    folder = Path(folder)
    meta = json.loads((folder / "deck.json").read_text(encoding="utf-8"))
    cards = [
        read_card(p)
        for p in sorted(folder.glob("card-*.md"))
        if not p.name.endswith(".broken")
    ]
    return Deck(
        name=meta["name"],
        description=meta.get("description", ""),
        cards=cards,
        metadata=meta,
        folder=folder,
    )
