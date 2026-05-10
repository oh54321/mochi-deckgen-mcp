from __future__ import annotations

import csv
from pathlib import Path

from deckgen.io.deck_fs import Deck


def export_csv(deck: Deck, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{deck.name}.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["front", "back", "tags"])
        for c in deck.cards:
            w.writerow([c.front_md, c.back_md, ",".join(c.tags)])
    return path
