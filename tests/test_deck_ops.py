from pathlib import Path

import pytest

from mochi_tools_mcp.local.deck_ops import (
    create_deck,
    delete_card,
    delete_deck,
    list_cards,
    list_decks,
    read_card,
    write_card,
)


def test_create_deck_writes_metadata(tmp_path: Path):
    info = create_deck(tmp_path, "Flags", description="World flags")
    assert (tmp_path / "raw" / "Flags" / "deck.json").exists()
    assert info["name"] == "Flags"


def test_write_and_read_card(tmp_path: Path):
    create_deck(tmp_path, "T")
    p = write_card(tmp_path, "T", 1, "Front?", "Back", tags=["x"])
    card = read_card(tmp_path, "T", 1)
    assert card["front_md"] == "Front?"
    assert card["back_md"] == "Back"
    assert card["tags"] == ["x"]
    assert Path(p).exists()


def test_list_cards_and_decks(tmp_path: Path):
    create_deck(tmp_path, "A")
    write_card(tmp_path, "A", 1, "Q1", "A1")
    write_card(tmp_path, "A", 2, "Q2", "A2")
    decks = list_decks(tmp_path)
    assert any(d["name"] == "A" and d["card_count"] == 2 for d in decks)
    cards = list_cards(tmp_path, "A")
    assert len(cards) == 2
    assert cards[0]["index"] == 1


def test_delete_card_soft_moves_to_trash(tmp_path: Path):
    create_deck(tmp_path, "A")
    write_card(tmp_path, "A", 1, "Q", "A")
    delete_card(tmp_path, "A", 1)
    assert not (tmp_path / "raw" / "A" / "card-001.md").exists()
    trashed = list((tmp_path / ".trash").rglob("card-001.md"))
    assert len(trashed) == 1


def test_delete_deck_soft_moves_folder(tmp_path: Path):
    create_deck(tmp_path, "A")
    delete_deck(tmp_path, "A")
    assert not (tmp_path / "raw" / "A").exists()
    assert any((tmp_path / ".trash").iterdir())


def test_create_deck_refuses_overwrite(tmp_path: Path):
    create_deck(tmp_path, "Z")
    with pytest.raises(FileExistsError):
        create_deck(tmp_path, "Z")
