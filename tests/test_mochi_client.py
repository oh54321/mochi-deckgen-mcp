import httpx
import pytest

from deckgen_mcp.mochi.client import MochiClient
from deckgen_mcp.mochi.errors import MochiAuthError, MochiNotFoundError


def _client(handler):
    transport = httpx.MockTransport(handler)
    return MochiClient(api_key="k", _transport=transport)


def test_list_decks(monkeypatch):
    def h(r):
        return httpx.Response(200, json={"docs": [{"id": "d1", "name": "Flags"}], "bookmark": None})

    c = _client(h)
    decks = c.list_decks()
    assert decks["docs"][0]["name"] == "Flags"


def test_get_card_404():
    def h(r):
        return httpx.Response(404, json={"error": "not found"})

    c = _client(h)
    with pytest.raises(MochiNotFoundError):
        c.get_card("missing")


def test_401_raises_auth():
    def h(r):
        return httpx.Response(401)

    c = _client(h)
    with pytest.raises(MochiAuthError):
        c.list_decks()


def test_429_retries_then_succeeds():
    calls = {"n": 0}

    def h(r):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json={"docs": [], "bookmark": None})

    c = _client(h)
    c.list_decks()
    assert calls["n"] == 3


def test_create_card_posts_json():
    captured = {}

    def h(r):
        captured["body"] = r.read().decode()
        return httpx.Response(200, json={"id": "c1", "content": "Q\n---\nA", "deck-id": "d1"})

    c = _client(h)
    out = c.create_card(deck_id="d1", content="Q\n---\nA")
    assert out["id"] == "c1"
    assert "deck-id" in captured["body"]
