import sqlite3
import tempfile
import zipfile
from pathlib import Path

from deckgen.exporters.anki import export_anki
from deckgen.io.deck_fs import read_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_apkg_contains_three_notes_and_media(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_anki(deck, tmp_path)
    assert out.name == "Sample.apkg"

    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
        assert "collection.anki2" in names
        assert "media" in names

        with tempfile.TemporaryDirectory() as d:
            z.extract("collection.anki2", d)
            con = sqlite3.connect(Path(d) / "collection.anki2")
            (n,) = con.execute("SELECT COUNT(*) FROM notes").fetchone()
            assert n == 3
