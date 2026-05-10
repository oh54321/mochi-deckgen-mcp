import httpx
import pytest

from deckgen_mcp.tools import mochi_tools


def test_collect_with_no_key_returns_error_stubs(monkeypatch):
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    tools = mochi_tools.collect()
    names = {t["name"] for t in tools}
    assert "mochi_list_decks" in names

    fn = next(t["fn"] for t in tools if t["name"] == "mochi_list_decks")
    out = fn()
    assert out.get("isError") is True
    assert "MOCHI_API_KEY" in out["content"][0]["text"]


def test_full_coverage_of_endpoints(monkeypatch):
    monkeypatch.setenv("MOCHI_API_KEY", "k")
    tools = mochi_tools.collect()
    names = {t["name"] for t in tools}
    expected = {
        "mochi_list_decks", "mochi_get_deck", "mochi_create_deck", "mochi_update_deck",
        "mochi_delete_deck", "mochi_trash_deck",
        "mochi_list_cards", "mochi_get_card", "mochi_create_card", "mochi_update_card",
        "mochi_delete_card", "mochi_trash_card",
        "mochi_add_attachment", "mochi_delete_attachment",
        "mochi_list_templates", "mochi_get_template", "mochi_create_template",
        "mochi_get_due_cards",
    }
    assert expected <= names
