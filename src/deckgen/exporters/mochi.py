from __future__ import annotations

import hashlib
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from deckgen.io.deck_fs import Card, Deck

IMAGE_RE = re.compile(r"!\[([^\]]*)\]\((images/[^)]+)\)")


def _short_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:8]


def _edn_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


@dataclass
class _Attachment:
    arcname: str          # path inside the zip: "attachments/<id>.png"
    attach_id: str        # the EDN @id used in card content
    abs_source: Path


def _card_content(card: Card, attachments_by_path: dict[str, _Attachment]) -> str:
    def repl(m: re.Match) -> str:
        alt, rel = m.group(1), m.group(2)
        att = attachments_by_path.get(rel)
        if att is None:
            return m.group(0)
        return f"![{alt}](@{att.attach_id})"

    front = IMAGE_RE.sub(repl, card.front_md)
    back = IMAGE_RE.sub(repl, card.back_md)
    return f"{front}\n---\n{back}"


def export_mochi(deck: Deck, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    attachments: dict[str, _Attachment] = {}
    for c in deck.cards:
        for rel in c.image_paths:
            rel_s = str(rel)
            if rel_s in attachments:
                continue
            src = deck.folder / rel
            if not src.exists():
                continue
            aid = _short_id(deck.name, rel_s)
            attachments[rel_s] = _Attachment(
                arcname=f"attachments/{aid}{src.suffix}",
                attach_id=aid,
                abs_source=src,
            )

    deck_id = _short_id(deck.name, "deck")

    lines: list[str] = ["{:version 2"]
    lines.append(f" :decks [{{:id {_edn_str(deck_id)} :name {_edn_str(deck.name)} :cards [")
    for i, c in enumerate(deck.cards):
        cid = _short_id(deck.name, str(i))
        name = c.front_md.splitlines()[0][:80] if c.front_md.splitlines() else f"Card {i+1}"
        content = _card_content(c, attachments)
        tag_vec = " ".join(_edn_str(t) for t in c.tags)
        lines.append(
            f"  {{:id {_edn_str(cid)} :name {_edn_str(name)} "
            f":content {_edn_str(content)} "
            f":deck-id {_edn_str(deck_id)} "
            f":tags [{tag_vec}]}}"
        )
    lines.append(" ]}]}")
    edn = "\n".join(lines)

    path = out_dir / f"{deck.name}.mochi"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("data.edn", edn)
        for att in attachments.values():
            z.write(att.abs_source, arcname=att.arcname)
    return path
