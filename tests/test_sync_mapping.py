from pathlib import Path

from deckgen_mcp.sync.mapping import Mapping, hash_text, load_mapping, save_mapping


def test_round_trip(tmp_path: Path):
    folder = tmp_path / "raw" / "Flags"
    folder.mkdir(parents=True)
    m = Mapping(deck_id="d1", deck_name_on_mochi="Flags", parent_id=None, template_id=None)
    m.cards["card-001.md"] = {"id": "c1", "content_hash": "sha1:abc"}
    m.images["images/jp.png"] = "sha1:def"
    save_mapping(folder, m)
    loaded = load_mapping(folder)
    assert loaded is not None
    assert loaded.deck_id == "d1"
    assert loaded.cards["card-001.md"]["id"] == "c1"


def test_missing_returns_none(tmp_path):
    assert load_mapping(tmp_path) is None


def test_hash_text_stable():
    assert hash_text("hello") == hash_text("hello")
    assert hash_text("a").startswith("sha1:")
