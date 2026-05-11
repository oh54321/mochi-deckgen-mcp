"""Extended tests for tools/mochi_tools.py to boost coverage."""

from __future__ import annotations

import base64

import httpx

from mochi_tools_mcp.tools import mochi_tools


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _tools_with_key(monkeypatch, handler):
    monkeypatch.setenv("MOCHI_API_KEY", "testkey")
    from mochi_tools_mcp.mochi.client import MochiClient

    original_init = MochiClient.__init__

    def patched_init(self, api_key, _transport=None):
        original_init(self, api_key, _transport=_mock_transport(handler))

    monkeypatch.setattr(MochiClient, "__init__", patched_init)
    return {t["name"]: t["fn"] for t in mochi_tools.collect()}


def test_mochi_list_decks(monkeypatch):
    def h(r):
        return httpx.Response(200, json={"docs": [{"id": "d1", "name": "Test"}], "bookmark": None})

    tools = _tools_with_key(monkeypatch, h)
    result = tools["mochi_list_decks"]()
    assert result["docs"][0]["id"] == "d1"


def test_mochi_get_deck(monkeypatch):
    def h(r):
        return httpx.Response(200, json={"id": "d1", "name": "Test"})

    tools = _tools_with_key(monkeypatch, h)
    result = tools["mochi_get_deck"](deck_id="d1")
    assert result["id"] == "d1"


def test_mochi_create_deck(monkeypatch):
    def h(r):
        return httpx.Response(200, json={"id": "d2", "name": "New"})

    tools = _tools_with_key(monkeypatch, h)
    result = tools["mochi_create_deck"](name="New")
    assert result["name"] == "New"


def test_mochi_update_deck(monkeypatch):
    def h(r):
        return httpx.Response(200, json={"id": "d1", "name": "Updated"})

    tools = _tools_with_key(monkeypatch, h)
    result = tools["mochi_update_deck"](deck_id="d1", name="Updated")
    assert result["name"] == "Updated"


def test_mochi_delete_deck(monkeypatch):
    def h(r):
        return httpx.Response(200, json={})

    tools = _tools_with_key(monkeypatch, h)
    result = tools["mochi_delete_deck"](deck_id="d1")
    assert result == {}


def test_mochi_trash_deck(monkeypatch):
    def h(r):
        return httpx.Response(200, json={"id": "d1"})

    tools = _tools_with_key(monkeypatch, h)
    result = tools["mochi_trash_deck"](deck_id="d1")
    assert result["id"] == "d1"


def test_mochi_trash_deck_no_key(monkeypatch):
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    tools = {t["name"]: t["fn"] for t in mochi_tools.collect()}
    result = tools["mochi_trash_deck"](deck_id="d1")
    assert result.get("isError") is True


def test_mochi_trash_card(monkeypatch):
    def h(r):
        return httpx.Response(200, json={"id": "c1"})

    tools = _tools_with_key(monkeypatch, h)
    result = tools["mochi_trash_card"](card_id="c1")
    assert result["id"] == "c1"


def test_mochi_trash_card_no_key(monkeypatch):
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    tools = {t["name"]: t["fn"] for t in mochi_tools.collect()}
    result = tools["mochi_trash_card"](card_id="c1")
    assert result.get("isError") is True


def test_mochi_add_attachment(monkeypatch):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="PNG")
    b64_content = base64.b64encode(buf.getvalue()).decode()

    def h(r):
        return httpx.Response(200, json={"id": "att1"})

    tools = _tools_with_key(monkeypatch, h)
    result = tools["mochi_add_attachment"](
        card_id="c1", filename="img.png", base64_content=b64_content, content_type="image/png"
    )
    assert result["id"] == "att1"


def test_mochi_add_attachment_no_key(monkeypatch):
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    tools = {t["name"]: t["fn"] for t in mochi_tools.collect()}
    result = tools["mochi_add_attachment"](
        card_id="c1", filename="img.png", base64_content="abc", content_type="image/png"
    )
    assert result.get("isError") is True
