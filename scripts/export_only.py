#!/usr/bin/env python3
"""Re-export an existing raw deck folder without regenerating cards."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from deckgen.config import DECKS_EXPORTED, DECKS_RAW
from deckgen.io.deck_fs import read_deck
from deckgen.pipeline.export import export_deck


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True)
    p.add_argument("--raw-root", default=str(DECKS_RAW))
    p.add_argument("--exported-root", default=str(DECKS_EXPORTED))
    p.add_argument("--format", action="append", choices=["mochi", "anki", "markdown", "csv", "all"])
    ns = p.parse_args()
    deck = read_deck(Path(ns.raw_root) / ns.name)
    out = export_deck(deck, out_root=Path(ns.exported_root), formats=ns.format or ["mochi"])
    for path in out:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
