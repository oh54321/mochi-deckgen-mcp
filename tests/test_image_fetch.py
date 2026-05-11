from __future__ import annotations

import io

import httpx
import pytest
from PIL import Image

from deckgen_mcp.local.image_fetch import fetch_image


def _png_bytes(size=(2000, 1500), color=(255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _transport(content: bytes, content_type: str, status: int = 200):
    return httpx.MockTransport(
        lambda r: httpx.Response(status, content=content, headers={"content-type": content_type})
    )


def test_fetch_resizes_to_max_edge(tmp_path, monkeypatch):
    transport = _transport(_png_bytes(), "image/png")
    monkeypatch.setattr("deckgen_mcp.local.image_fetch._client", httpx.Client(transport=transport))

    out = fetch_image("https://x/y.png", tmp_path, max_edge_px=512)
    assert out is not None
    img = Image.open(out)
    assert max(img.size) == 512


def test_fetch_dedups_by_content_hash(tmp_path, monkeypatch):
    content = _png_bytes()
    transport = _transport(content, "image/png")
    monkeypatch.setattr("deckgen_mcp.local.image_fetch._client", httpx.Client(transport=transport))

    a = fetch_image("https://x/a.png", tmp_path)
    b = fetch_image("https://x/b.png", tmp_path)
    assert a == b  # same filename due to content hash


def test_fetch_returns_none_on_http_error(tmp_path, monkeypatch):
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    monkeypatch.setattr("deckgen_mcp.local.image_fetch._client", httpx.Client(transport=transport))

    assert fetch_image("https://x/y.png", tmp_path) is None


def test_svg_conversion_when_cairosvg_present(tmp_path, monkeypatch):
    pytest.importorskip("cairosvg")
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
        b'<rect width="100" height="100" fill="red"/></svg>'
    )
    transport = _transport(svg, "image/svg+xml")
    monkeypatch.setattr("deckgen_mcp.local.image_fetch._client", httpx.Client(transport=transport))

    out = fetch_image("https://x/y.svg", tmp_path)
    assert out is not None
    assert out.suffix == ".png"
    assert Image.open(out).size[0] > 0
