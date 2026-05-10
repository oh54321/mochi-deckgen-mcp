import csv as _csv
from pathlib import Path

from deckgen.exporters.csv_export import export_csv
from deckgen.io.deck_fs import read_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_export_csv_three_rows(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_csv(deck, tmp_path)
    assert out.name == "Sample.csv"
    rows = list(_csv.reader(out.open(encoding="utf-8")))
    assert rows[0] == ["front", "back", "tags"]
    assert len(rows) == 4
    assert "Japan" in rows[1][1]
    assert rows[1][2] == "asia,island-nations"
