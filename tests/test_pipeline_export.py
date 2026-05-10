from pathlib import Path

from deckgen.io.deck_fs import read_deck
from deckgen.pipeline.export import export_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_export_deck_all_formats_writes_four_files(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_deck(deck, out_root=tmp_path, formats=["mochi", "anki", "markdown", "csv"])
    names = {p.suffix for p in out}
    assert names == {".mochi", ".apkg", ".zip", ".csv"}
    for p in out:
        assert p.parent.name == "Sample"


def test_export_deck_default_mochi_only(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_deck(deck, out_root=tmp_path, formats=["mochi"])
    assert len(out) == 1 and out[0].suffix == ".mochi"


def test_export_deck_all_alias(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_deck(deck, out_root=tmp_path, formats=["all"])
    assert {p.suffix for p in out} == {".mochi", ".apkg", ".zip", ".csv"}
