from pathlib import Path

from deckgen.io.deck_fs import read_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_read_deck_loads_metadata_and_cards():
    deck = read_deck(FIXTURE)
    assert deck.name == "Sample"
    assert deck.description.startswith("Three-card")
    assert len(deck.cards) == 3
    assert deck.cards[0].source_path.name == "card-001.md"
    assert deck.cards[2].source_path.name == "card-003.md"


def test_read_deck_skips_broken_files(tmp_path):
    (tmp_path / "deck.json").write_text('{"name":"X","description":"d"}')
    (tmp_path / "card-001.md").write_text("front\n---\n\nback")
    (tmp_path / "card-002.md.broken").write_text("garbage")
    deck = read_deck(tmp_path)
    assert len(deck.cards) == 1
