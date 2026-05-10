import zipfile
from pathlib import Path

from deckgen.exporters.mochi import export_mochi
from deckgen.io.deck_fs import read_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_mochi_zip_has_data_edn_and_images(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_mochi(deck, tmp_path)
    assert out.name == "Sample.mochi"
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
        assert "data.edn" in names
        assert any(n.startswith("attachments/") for n in names)
        edn = z.read("data.edn").decode("utf-8")

    assert ":version" in edn
    assert ":decks" in edn
    assert ":cards" in edn
    assert "Japan" in edn
    assert "\\\\int_0^1" in edn or "\\int_0^1" in edn
