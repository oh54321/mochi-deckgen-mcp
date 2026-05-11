"""Extended tests for tools/local_tools.py to boost coverage."""

from __future__ import annotations

import base64
from pathlib import Path

import httpx

from mochi_deckgen_mcp.tools import local_tools


def _tools(tmp_path: Path, monkeypatch) -> dict:
    monkeypatch.setenv("DECKGEN_DECKS_ROOT", str(tmp_path))
    return {t["name"]: t["fn"] for t in local_tools.collect()}


def test_read_card(tmp_path: Path, monkeypatch):
    tools = _tools(tmp_path, monkeypatch)
    tools["local_create_deck"](name="T")
    tools["local_write_card"](deck="T", index=1, front_md="Q", back_md="A")
    card = tools["local_read_card"](deck="T", index=1)
    assert card["front_md"] == "Q"


def test_delete_card(tmp_path: Path, monkeypatch):
    tools = _tools(tmp_path, monkeypatch)
    tools["local_create_deck"](name="T")
    tools["local_write_card"](deck="T", index=1, front_md="Q", back_md="A")
    result = tools["local_delete_card"](deck="T", index=1)
    assert "trashed_to" in result


def test_delete_deck(tmp_path: Path, monkeypatch):
    tools = _tools(tmp_path, monkeypatch)
    tools["local_create_deck"](name="T")
    result = tools["local_delete_deck"](name="T")
    assert "trashed_to" in result


def test_fetch_image_network_error(tmp_path: Path, monkeypatch):
    """fetch_image returns None on HTTP error."""
    import mochi_deckgen_mcp.local.image_fetch as image_fetch_mod

    def bad_get(url, **kwargs):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(image_fetch_mod._client, "get", bad_get)
    tools = _tools(tmp_path, monkeypatch)
    result = tools["local_fetch_image"](url="http://example.com/img.png", deck="T")
    assert result["path"] is None


def test_fetch_image_success(tmp_path: Path, monkeypatch):
    """fetch_image returns a path on success."""
    import io

    from PIL import Image

    import mochi_deckgen_mcp.local.image_fetch as image_fetch_mod

    buf = io.BytesIO()
    Image.new("RGB", (100, 100), color=(255, 0, 0)).save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    fake_response = httpx.Response(200, content=img_bytes, headers={"content-type": "image/jpeg"})

    monkeypatch.setattr(image_fetch_mod._client, "get", lambda url, **kwargs: fake_response)
    monkeypatch.setattr("httpx.Response.raise_for_status", lambda self: None)
    tools = _tools(tmp_path, monkeypatch)
    result = tools["local_fetch_image"](url="http://example.com/img.jpg", deck="T")
    assert result["path"] is not None


def test_import_image_base64(tmp_path: Path, monkeypatch):
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (50, 50), color=(0, 255, 0)).save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()

    tools = _tools(tmp_path, monkeypatch)
    tools["local_create_deck"](name="ImgDeck")
    result = tools["local_import_image"](deck="ImgDeck", base64_data=b64, filename="test.png")
    assert result["path"] is not None


def test_check_malformed_single_card(tmp_path: Path, monkeypatch):
    tools = _tools(tmp_path, monkeypatch)
    tools["local_create_deck"](name="T")
    tools["local_write_card"](deck="T", index=1, front_md="Q", back_md="A")
    result = tools["local_check_malformed"](deck="T", index=1)
    assert result is not None


def test_check_malformed_all_cards(tmp_path: Path, monkeypatch):
    tools = _tools(tmp_path, monkeypatch)
    tools["local_create_deck"](name="T")
    tools["local_write_card"](deck="T", index=1, front_md="Q1", back_md="A1")
    tools["local_write_card"](deck="T", index=2, front_md="Q2", back_md="A2")
    result = tools["local_check_malformed"](deck="T")
    assert isinstance(result, dict)
    assert 1 in result
    assert 2 in result


def test_fetch_wikipedia_image(tmp_path: Path, monkeypatch):
    import mochi_deckgen_mcp.local.image_wikipedia as wiki_mod

    monkeypatch.setattr(wiki_mod, "fetch_wikipedia_image", lambda query, dest: None)
    tools = _tools(tmp_path, monkeypatch)
    result = tools["local_fetch_wikipedia_image"](query="Eiffel Tower", deck="T")
    assert result is None
