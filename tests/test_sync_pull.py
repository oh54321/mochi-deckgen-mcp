from __future__ import annotations

from mochi_tools_mcp.sync.pull import pull_deck


class FakeMochi:
    def get_deck(self, deck_id):
        return {"id": deck_id, "name": "Flags"}

    def list_cards(self, deck_id=None, bookmark=None):
        return {
            "docs": [
                {"id": "c1", "content": "What flag?\n\n---\n\nJapan\n\n![](@media/jp.png)"},
                {"id": "c2", "content": "Capital of France?\n\n---\n\nParis"},
            ],
            "bookmark": None,
        }


def test_pull_writes_cards_and_mapping(tmp_path):
    pull_deck(tmp_path, "d1", FakeMochi())
    folder = tmp_path / "raw" / "Flags"
    assert (folder / "card-001.md").exists()
    assert (folder / "card-002.md").exists()
    assert (folder / ".mochi.json").exists()


def test_pull_rewrites_media_refs_and_warns(tmp_path):
    pull_deck(tmp_path, "d1", FakeMochi())
    folder = tmp_path / "raw" / "Flags"
    first = (folder / "card-001.md").read_text()
    assert "images/jp.png" in first
    assert "@media/" not in first
    warn = (folder / "attachments-not-downloaded.txt").read_text()
    assert "jp.png" in warn
