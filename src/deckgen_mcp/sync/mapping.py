from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Mapping:
    deck_id: str
    deck_name_on_mochi: str
    parent_id: str | None = None
    template_id: str | None = None
    cards: dict[str, dict[str, Any]] = field(default_factory=dict)
    images: dict[str, str] = field(default_factory=dict)
    last_push_at: str | None = None


def load_mapping(deck_folder: Path) -> Mapping | None:
    p = Path(deck_folder) / ".mochi.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    return Mapping(**data)


def save_mapping(deck_folder: Path, m: Mapping) -> None:
    p = Path(deck_folder) / ".mochi.json"
    p.write_text(json.dumps(m.__dict__, indent=2))


def hash_text(text: str) -> str:
    return "sha1:" + hashlib.sha1(text.encode("utf-8")).hexdigest()


def hash_bytes(data: bytes) -> str:
    return "sha1:" + hashlib.sha1(data).hexdigest()
