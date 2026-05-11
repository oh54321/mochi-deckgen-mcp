from pathlib import Path

import pytest

from deckgen_mcp.local.deck_fs import read_card, read_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_parses_front_back_tags_and_image():
    card = read_card(FIXTURE / "card-001.md")
    assert card.front_md.startswith("What country has this flag?")
    assert "![](images/jp.png)" in card.front_md
    assert card.back_md.startswith("Japan")
    assert card.tags == ["asia", "island-nations"]
    assert card.image_paths == [Path("images/jp.png")]


def test_parses_math_card_no_tags_no_images():
    card = read_card(FIXTURE / "card-002.md")
    assert "\\int_0^1" in card.front_md
    assert card.back_md.strip() == "$\\frac{1}{2}$"
    assert card.tags == []
    assert card.image_paths == []


def test_only_first_dashes_separate_sides():
    card = read_card(FIXTURE / "card-003.md")
    assert "in front body literal" in card.front_md
    assert card.back_md.startswith("Back")
    assert card.tags == ["edge-case"]


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_card(FIXTURE / "does-not-exist.md")


def test_read_deck_returns_all_cards():
    deck = read_deck(FIXTURE)
    assert deck.name
    assert len(deck.cards) == 3
