from pathlib import Path
from unittest.mock import patch

import httpx

from deckgen.io.image_fetch import fetch_image


def test_fetch_image_writes_file(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"\x89PNG\r\n\x1a\nbytes", headers={"content-type": "image/png"})

    transport = httpx.MockTransport(handler)
    with patch("deckgen.io.image_fetch._client", httpx.Client(transport=transport)):
        out = fetch_image("https://example.com/flag.png", tmp_path / "images")
    assert out.exists()
    assert out.suffix == ".png"
    assert out.read_bytes().startswith(b"\x89PNG")


def test_fetch_image_returns_none_on_failure(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    with patch("deckgen.io.image_fetch._client", httpx.Client(transport=transport)):
        out = fetch_image("https://example.com/missing.png", tmp_path / "images")
    assert out is None
