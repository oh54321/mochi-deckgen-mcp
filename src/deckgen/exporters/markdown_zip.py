from __future__ import annotations

import zipfile
from pathlib import Path

from deckgen.io.deck_fs import Deck


def export_markdown_zip(deck: Deck, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{deck.name}.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(deck.folder.rglob("*")):
            if p.is_dir() or p.name.endswith(".broken"):
                continue
            z.write(p, arcname=p.relative_to(deck.folder))
    return path
