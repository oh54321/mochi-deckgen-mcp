from __future__ import annotations

import hashlib
import re
from pathlib import Path

import genanki

from deckgen.io.deck_fs import Deck

MODEL_TEMPLATE = {
    "name": "DeckgenBasic",
    "fields": [{"name": "Front"}, {"name": "Back"}],
    "templates": [
        {
            "name": "Card 1",
            "qfmt": "{{Front}}",
            "afmt": "{{FrontSide}}<hr id='answer'>{{Back}}",
        }
    ],
}

IMAGE_RE = re.compile(r"!\[[^\]]*\]\((images/[^)]+)\)")


def _stable_id(name: str, salt: str) -> int:
    return int(hashlib.sha1(f"{name}|{salt}".encode()).hexdigest()[:8], 16)


def _md_to_anki(text: str) -> str:
    return IMAGE_RE.sub(lambda m: f'<img src="{Path(m.group(1)).name}">', text)


def export_anki(deck: Deck, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model = genanki.Model(
        _stable_id(deck.name, "model"),
        MODEL_TEMPLATE["name"],
        fields=MODEL_TEMPLATE["fields"],
        templates=MODEL_TEMPLATE["templates"],
    )
    adeck = genanki.Deck(_stable_id(deck.name, "deck"), deck.name)

    media: list[str] = []
    for card in deck.cards:
        note = genanki.Note(
            model=model,
            fields=[_md_to_anki(card.front_md), _md_to_anki(card.back_md)],
            tags=card.tags,
        )
        adeck.add_note(note)
        for ip in card.image_paths:
            abs_path = deck.folder / ip
            if abs_path.exists():
                media.append(str(abs_path))

    path = out_dir / f"{deck.name}.apkg"
    genanki.Package(adeck, media_files=media).write_to_file(str(path))
    return path
