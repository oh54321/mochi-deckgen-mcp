from __future__ import annotations

from mochi_deckgen_mcp.local.deck_ops import create_deck, write_card
from mochi_deckgen_mcp.sync.diff import sync_status
from mochi_deckgen_mcp.sync.mapping import Mapping, hash_text, save_mapping


class FakeMochi:
    def __init__(self, cards):
        self._cards = cards

    def list_cards(self, deck_id=None, bookmark=None):
        return {"docs": self._cards, "bookmark": None}


def test_status_reports_categories(tmp_path):
    create_deck(tmp_path, "T")
    write_card(tmp_path, "T", 1, "Q1", "A1")
    write_card(tmp_path, "T", 2, "Q2-NEW", "A2")

    mapping = Mapping(deck_id="d1", deck_name_on_mochi="T")
    mapping.cards["card-001.md"] = {"id": "c1", "content_hash": hash_text("Q1\n\n---\n\nA1")}
    mapping.cards["card-002.md"] = {"id": "c2", "content_hash": hash_text("OLD")}
    save_mapping(tmp_path / "raw" / "T", mapping)

    fm = FakeMochi(
        [
            {"id": "c1", "content": "Q1\n\n---\n\nA1"},
            {"id": "c2", "content": "Q2-NEW\n\n---\n\nA2"},
            {"id": "c3", "content": "extra\n\n---\n\nx"},
        ]
    )
    status = sync_status(tmp_path, "T", fm)
    changed = [s["name"] for s in status if s["status"] == "changed-locally"]
    assert "card-002.md" in changed
    assert any(s["status"] == "new-remotely" for s in status)
