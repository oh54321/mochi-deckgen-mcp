from pathlib import Path

from mochi_deckgen_mcp.tools import local_tools


def test_register_returns_tool_callables():
    tools = local_tools.collect()
    names = {t["name"] for t in tools}
    expected = {
        "local_create_deck",
        "local_write_card",
        "local_read_card",
        "local_list_decks",
        "local_list_cards",
        "local_delete_card",
        "local_delete_deck",
        "local_fetch_image",
        "local_fetch_wikipedia_image",
        "local_import_image",
        "local_check_malformed",
    }
    assert expected <= names


def test_local_create_and_write_via_tool(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DECKGEN_DECKS_ROOT", str(tmp_path))
    tools = {t["name"]: t["fn"] for t in local_tools.collect()}
    tools["local_create_deck"](name="T")
    tools["local_write_card"](deck="T", index=1, front_md="Q", back_md="A")
    cards = tools["local_list_cards"](deck="T")
    assert len(cards) == 1
