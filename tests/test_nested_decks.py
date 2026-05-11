from __future__ import annotations

from pathlib import Path

import pytest

from mochi_deckgen_mcp.local.deck_ops import (
    create_deck,
    delete_deck,
    list_cards,
    list_decks,
    read_card,
    write_card,
)
from mochi_deckgen_mcp.sync.push import push_deck


def test_create_nested_deck(tmp_path: Path):
    create_deck(tmp_path, "Languages/Spanish/Vocabulary")
    assert (tmp_path / "raw" / "Languages" / "Spanish" / "Vocabulary" / "deck.json").exists()


def test_list_decks_returns_full_paths(tmp_path: Path):
    create_deck(tmp_path, "Flags")
    create_deck(tmp_path, "Languages/Spanish")
    create_deck(tmp_path, "Languages/Spanish/Vocabulary")
    names = [d["name"] for d in list_decks(tmp_path)]
    assert "Flags" in names
    assert "Languages/Spanish" in names
    assert "Languages/Spanish/Vocabulary" in names


def test_list_decks_reports_depth_and_parent(tmp_path: Path):
    create_deck(tmp_path, "Languages/Spanish")
    rows = list_decks(tmp_path)
    spanish = next(r for r in rows if r["name"] == "Languages/Spanish")
    assert spanish["depth"] == 1
    assert spanish["parent_name"] == "Languages"


def test_intermediates_auto_promoted_to_decks(tmp_path: Path):
    # Auto-promote intermediates so Mochi hierarchy matches local structure on push.
    create_deck(tmp_path, "A/B/C")
    names = {d["name"] for d in list_decks(tmp_path)}
    assert names == {"A", "A/B", "A/B/C"}


def test_write_and_read_card_in_nested_deck(tmp_path: Path):
    create_deck(tmp_path, "Languages/Spanish")
    write_card(tmp_path, "Languages/Spanish", 1, "el gato", "the cat", tags=["nouns"])
    card = read_card(tmp_path, "Languages/Spanish", 1)
    assert card["front_md"] == "el gato"
    assert card["back_md"] == "the cat"
    cards = list_cards(tmp_path, "Languages/Spanish")
    assert len(cards) == 1


def test_delete_nested_deck(tmp_path: Path):
    create_deck(tmp_path, "A/B")
    delete_deck(tmp_path, "A/B")
    assert not (tmp_path / "raw" / "A" / "B").exists()
    # Soft-deleted folder name should encode the slash
    trashed = list((tmp_path / ".trash").iterdir())
    assert any("A__B" in t.name for t in trashed)


def test_create_deck_refuses_overwrite_for_nested(tmp_path: Path):
    create_deck(tmp_path, "A/B")
    with pytest.raises(FileExistsError):
        create_deck(tmp_path, "A/B")


class FakeMochi:
    def __init__(self) -> None:
        self.created_decks: list = []
        self.created_cards: list = []
        self.next_id = 0

    def create_deck(self, name, parent_id=None, **extra):
        self.next_id += 1
        d = {"id": f"d{self.next_id}", "name": name, "parent-id": parent_id}
        self.created_decks.append(d)
        return d

    def create_card(self, deck_id, content, **extra):
        self.next_id += 1
        c = {"id": f"c{self.next_id}", "deck-id": deck_id, "content": content, **extra}
        self.created_cards.append(c)
        return c

    def update_card(self, card_id, **fields):
        return {"id": card_id, **fields}


def test_push_nested_deck_creates_parents_first(tmp_path: Path):
    create_deck(tmp_path, "Languages")
    create_deck(tmp_path, "Languages/Spanish")
    write_card(tmp_path, "Languages/Spanish", 1, "el gato", "the cat")

    fm = FakeMochi()
    result = push_deck(tmp_path, "Languages/Spanish", fm)

    # Two decks created on Mochi: parent first, then child with parent_id wired
    assert len(fm.created_decks) == 2
    assert fm.created_decks[0]["name"] == "Languages"
    assert fm.created_decks[1]["name"] == "Spanish"
    assert fm.created_decks[1]["parent-id"] == fm.created_decks[0]["id"]
    assert result["created"] == 1


def test_push_uses_leaf_name_on_mochi(tmp_path: Path):
    create_deck(tmp_path, "A/B/C")
    write_card(tmp_path, "A/B/C", 1, "q", "a")
    fm = FakeMochi()
    push_deck(tmp_path, "A/B/C", fm)
    # 3 decks created: A, B, C — only the leaf names appear, hierarchy via parent-id
    assert [d["name"] for d in fm.created_decks] == ["A", "B", "C"]


def test_push_writes_manual_tags(tmp_path: Path):
    create_deck(tmp_path, "T")
    write_card(tmp_path, "T", 1, "q", "a", tags=["foo", "bar"])
    fm = FakeMochi()
    push_deck(tmp_path, "T", fm)
    assert fm.created_cards[0].get("manual_tags") == ["foo", "bar"]
    # Body should not include the Tags: line
    assert "Tags:" not in fm.created_cards[0]["content"]
