"""Extended tests for tools/sync_tools.py to boost coverage."""

from __future__ import annotations

from pathlib import Path

import httpx

from deckgen_mcp.tools import sync_tools


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _tools_with_key(tmp_path: Path, monkeypatch, handler=None):
    monkeypatch.setenv("DECKGEN_DECKS_ROOT", str(tmp_path))
    monkeypatch.setenv("MOCHI_API_KEY", "testkey")
    if handler is not None:
        from deckgen_mcp.mochi.client import MochiClient

        original_init = MochiClient.__init__

        def patched_init(self, api_key, _transport=None):
            original_init(self, api_key, _transport=_mock_transport(handler))

        monkeypatch.setattr(MochiClient, "__init__", patched_init)
    return {t["name"]: t["fn"] for t in sync_tools.collect()}


def test_sync_link(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DECKGEN_DECKS_ROOT", str(tmp_path))

    # create a deck folder first
    deck_folder = tmp_path / "raw" / "MyDeck"
    deck_folder.mkdir(parents=True)

    tools = {t["name"]: t["fn"] for t in sync_tools.collect()}
    result = tools["sync_link"](deck="MyDeck", deck_id="d123", deck_name_on_mochi="My Deck")
    assert result["deck_id"] == "d123"
    assert "MyDeck" in result["linked"]


def test_sync_link_default_name(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DECKGEN_DECKS_ROOT", str(tmp_path))

    deck_folder = tmp_path / "raw" / "Flags"
    deck_folder.mkdir(parents=True)

    tools = {t["name"]: t["fn"] for t in sync_tools.collect()}
    result = tools["sync_link"](deck="Flags", deck_id="d999")
    assert result["deck_id"] == "d999"


def test_sync_pull_without_auth(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DECKGEN_DECKS_ROOT", str(tmp_path))
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    tools = {t["name"]: t["fn"] for t in sync_tools.collect()}
    result = tools["sync_pull_deck"](deck_id="d1")
    assert result.get("isError") is True


def test_sync_status_without_auth(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DECKGEN_DECKS_ROOT", str(tmp_path))
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    tools = {t["name"]: t["fn"] for t in sync_tools.collect()}
    result = tools["sync_status"](deck="SomeDeck")
    assert result.get("isError") is True
