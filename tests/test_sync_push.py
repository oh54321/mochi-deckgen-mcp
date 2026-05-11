from mochi_deckgen_mcp.local.deck_ops import create_deck, write_card
from mochi_deckgen_mcp.sync.push import push_deck


class FakeMochi:
    def __init__(self):
        self.created_decks: list = []
        self.created_cards: list = []
        self.updated_cards: list = []
        self.next_id = 0

    def create_deck(self, name, parent_id=None, **extra):
        self.next_id += 1
        d = {"id": f"d{self.next_id}", "name": name, "parent-id": parent_id}
        self.created_decks.append(d)
        return d

    def create_card(self, deck_id, content, template_id=None, fields=None, **extra):
        self.next_id += 1
        c = {"id": f"c{self.next_id}", "deck-id": deck_id, "content": content, **extra}
        self.created_cards.append(c)
        return c

    def update_card(self, card_id, **fields):
        self.updated_cards.append({"id": card_id, **fields})
        return {"id": card_id, **fields}


def test_first_push_creates_everything(tmp_path):
    create_deck(tmp_path, "T")
    write_card(tmp_path, "T", 1, "Q1", "A1")
    write_card(tmp_path, "T", 2, "Q2", "A2")

    fm = FakeMochi()
    result = push_deck(tmp_path, "T", fm)
    assert len(fm.created_decks) == 1
    assert len(fm.created_cards) == 2
    assert result["created"] == 2
    assert (tmp_path / "raw" / "T" / ".mochi.json").exists()


def test_second_push_skips_unchanged(tmp_path):
    create_deck(tmp_path, "T")
    write_card(tmp_path, "T", 1, "Q1", "A1")
    fm = FakeMochi()
    push_deck(tmp_path, "T", fm)

    fm2 = FakeMochi()
    result = push_deck(tmp_path, "T", fm2)
    assert result["created"] == 0
    assert result["updated"] == 0


def test_second_push_updates_changed(tmp_path):
    create_deck(tmp_path, "T")
    write_card(tmp_path, "T", 1, "Q1", "A1")
    fm = FakeMochi()
    push_deck(tmp_path, "T", fm)

    write_card(tmp_path, "T", 1, "Q1", "A1-NEW")
    fm2 = FakeMochi()
    result = push_deck(tmp_path, "T", fm2)
    assert result["updated"] == 1
    assert len(fm2.updated_cards) == 1
