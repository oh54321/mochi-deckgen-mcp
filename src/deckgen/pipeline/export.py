from __future__ import annotations

from pathlib import Path

from deckgen.exporters.anki import export_anki
from deckgen.exporters.csv_export import export_csv
from deckgen.exporters.markdown_zip import export_markdown_zip
from deckgen.exporters.mochi import export_mochi
from deckgen.io.deck_fs import Deck

ALL_FORMATS = ("mochi", "anki", "markdown", "csv")
_EXPORTERS = {
    "mochi": export_mochi,
    "anki": export_anki,
    "markdown": export_markdown_zip,
    "csv": export_csv,
}


def export_deck(deck: Deck, *, out_root: Path, formats: list[str]) -> list[Path]:
    if "all" in formats:
        formats = list(ALL_FORMATS)
    out_dir = Path(out_root) / deck.name
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt in formats:
        if fmt not in _EXPORTERS:
            raise ValueError(f"unknown format: {fmt}")
        written.append(_EXPORTERS[fmt](deck, out_dir))
    return written
