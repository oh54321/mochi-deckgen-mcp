"""Extended tests for mochi/client.py to boost coverage."""

from __future__ import annotations

import httpx
import pytest

from mochi_deckgen_mcp.mochi.client import MochiClient
from mochi_deckgen_mcp.mochi.errors import (
    MochiError,
    MochiRateLimitError,
    MochiServerError,
)


def _client(handler) -> MochiClient:
    transport = httpx.MockTransport(handler)
    return MochiClient(api_key="k", _transport=transport)


def test_context_manager():
    def h(r):
        return httpx.Response(200, json={"docs": []})

    with _client(h) as c:
        result = c.list_decks()
    assert "docs" in result


def test_list_decks_with_bookmark():
    captured = {}

    def h(r):
        captured["url"] = str(r.url)
        return httpx.Response(200, json={"docs": [], "bookmark": None})

    c = _client(h)
    c.list_decks(bookmark="bm123")
    assert "bookmark=bm123" in captured["url"]


def test_get_deck():
    def h(r):
        return httpx.Response(200, json={"id": "d1", "name": "Test"})

    c = _client(h)
    result = c.get_deck("d1")
    assert result["id"] == "d1"


def test_create_deck_with_parent():
    captured = {}

    def h(r):
        import json

        captured["body"] = json.loads(r.read())
        return httpx.Response(200, json={"id": "d2", "name": "Child"})

    c = _client(h)
    c.create_deck("Child", parent_id="d1")
    assert captured["body"]["parent-id"] == "d1"


def test_update_deck():
    def h(r):
        return httpx.Response(200, json={"id": "d1", "name": "Updated"})

    c = _client(h)
    result = c.update_deck("d1", name="Updated")
    assert result["name"] == "Updated"


def test_delete_deck():
    def h(r):
        return httpx.Response(200, json={})

    c = _client(h)
    result = c.delete_deck("d1")
    assert result == {}


def test_trash_deck():
    captured = {}

    def h(r):
        import json

        captured["body"] = json.loads(r.read())
        return httpx.Response(200, json={"id": "d1"})

    c = _client(h)
    c.trash_deck("d1", "2026-01-01T00:00:00Z")
    assert "trashed?" in captured["body"]


def test_list_cards_with_params():
    captured = {}

    def h(r):
        captured["url"] = str(r.url)
        return httpx.Response(200, json={"docs": [], "bookmark": None})

    c = _client(h)
    c.list_cards(deck_id="d1", bookmark="bm2")
    assert "deck-id=d1" in captured["url"]
    assert "bookmark=bm2" in captured["url"]


def test_get_card():
    def h(r):
        return httpx.Response(200, json={"id": "c1", "content": "Q\n---\nA"})

    c = _client(h)
    result = c.get_card("c1")
    assert result["id"] == "c1"


def test_create_card_with_template_and_fields():
    captured = {}

    def h(r):
        import json

        captured["body"] = json.loads(r.read())
        return httpx.Response(200, json={"id": "c2"})

    c = _client(h)
    c.create_card("d1", "Q\n---\nA", template_id="t1", fields={"Front": "Q", "Back": "A"})
    assert captured["body"]["template-id"] == "t1"
    assert "fields" in captured["body"]


def test_update_card():
    def h(r):
        return httpx.Response(200, json={"id": "c1", "content": "Updated"})

    c = _client(h)
    result = c.update_card("c1", content="Updated")
    assert result["content"] == "Updated"


def test_delete_card():
    def h(r):
        return httpx.Response(200, json={})

    c = _client(h)
    result = c.delete_card("c1")
    assert result == {}


def test_trash_card():
    captured = {}

    def h(r):
        import json

        captured["body"] = json.loads(r.read())
        return httpx.Response(200, json={"id": "c1"})

    c = _client(h)
    c.trash_card("c1", "2026-01-01T00:00:00Z")
    assert "trashed?" in captured["body"]


def test_add_attachment():
    def h(r):
        return httpx.Response(200, json={"id": "att1"})

    c = _client(h)
    result = c.add_attachment("c1", "image.png", b"fake-image", "image/png")
    assert result["id"] == "att1"


def test_delete_attachment():
    def h(r):
        return httpx.Response(200, json={})

    c = _client(h)
    result = c.delete_attachment("c1", "image.png")
    assert result == {}


def test_list_templates():
    def h(r):
        return httpx.Response(200, json={"docs": []})

    c = _client(h)
    result = c.list_templates()
    assert "docs" in result


def test_get_template():
    def h(r):
        return httpx.Response(200, json={"id": "t1", "name": "Basic"})

    c = _client(h)
    result = c.get_template("t1")
    assert result["id"] == "t1"


def test_create_template():
    def h(r):
        return httpx.Response(200, json={"id": "t2", "name": "Custom"})

    c = _client(h)
    result = c.create_template("Custom", "{{Front}}\n---\n{{Back}}")
    assert result["name"] == "Custom"


def test_create_template_with_fields():
    captured = {}

    def h(r):
        import json

        captured["body"] = json.loads(r.read())
        return httpx.Response(200, json={"id": "t3"})

    c = _client(h)
    c.create_template("T", "content", fields={"Front": {}, "Back": {}})
    assert "fields" in captured["body"]


def test_get_due_cards_no_deck():
    def h(r):
        return httpx.Response(200, json={"docs": []})

    c = _client(h)
    result = c.get_due_cards()
    assert "docs" in result


def test_get_due_cards_with_deck():
    captured = {}

    def h(r):
        captured["url"] = str(r.url)
        return httpx.Response(200, json={"docs": []})

    c = _client(h)
    c.get_due_cards(deck_id="d1")
    assert "/due/d1" in captured["url"]


def test_500_retries_then_raises_server_error():
    calls = {"n": 0}

    def h(r):
        calls["n"] += 1
        return httpx.Response(500)

    c = _client(h)
    with pytest.raises(MochiServerError):
        c.list_decks()
    assert calls["n"] == 5


def test_429_exhausts_retries():
    calls = {"n": 0}

    def h(r):
        calls["n"] += 1
        return httpx.Response(429)

    c = _client(h)
    with pytest.raises(MochiRateLimitError):
        c.list_decks()
    assert calls["n"] == 5


def test_transport_error_retries_then_raises(monkeypatch):
    calls = {"n": 0}

    def h(r):
        calls["n"] += 1
        raise httpx.ConnectError("refused")

    c = _client(h)
    monkeypatch.setattr("time.sleep", lambda _: None)
    with pytest.raises(MochiError, match="transport error"):
        c.list_decks()
    assert calls["n"] == 5


def test_empty_response_returns_empty_dict():
    def h(r):
        return httpx.Response(200, content=b"")

    c = _client(h)
    result = c.delete_deck("d1")
    assert result == {}
