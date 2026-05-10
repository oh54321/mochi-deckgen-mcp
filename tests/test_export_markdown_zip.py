import zipfile
from pathlib import Path

from deckgen.exporters.markdown_zip import export_markdown_zip
from deckgen.io.deck_fs import read_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_zip_contains_all_card_files_and_images(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_markdown_zip(deck, tmp_path)
    assert out.name == "Sample.zip"
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
    assert "card-001.md" in names
    assert "card-002.md" in names
    assert "card-003.md" in names
    assert "deck.json" in names
    assert "images/jp.png" in names
