from __future__ import annotations

import io as _io
from pathlib import Path

import httpx
from PIL import Image as _Image

from deckgen_mcp.local.image_wikipedia import fetch_wikipedia_image

_JAPAN_THUMBNAIL = "https://upload.wikimedia.org/Flag_of_Japan.png"


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "action=query" in url and "Japan" in url:
        return httpx.Response(
            200,
            json={
                "query": {
                    "pages": {
                        "1": {
                            "title": "Japan",
                            "thumbnail": {"source": _JAPAN_THUMBNAIL, "width": 800},
                            "pageimage": "Flag_of_Japan.png",
                            "imageinfo": [
                                {
                                    "url": _JAPAN_THUMBNAIL,
                                    "extmetadata": {
                                        "Artist": {"value": "Government of Japan"},
                                        "LicenseShortName": {"value": "Public domain"},
                                    },
                                }
                            ],
                        }
                    }
                }
            },
        )
    if url.endswith("Flag_of_Japan.png"):
        buf = _io.BytesIO()
        _Image.new("RGB", (100, 60), (255, 0, 0)).save(buf, format="PNG")
        return httpx.Response(200, content=buf.getvalue(), headers={"content-type": "image/png"})
    if "Nonexistent" in url:
        return httpx.Response(200, json={"query": {"pages": {"-1": {"missing": ""}}}})
    return httpx.Response(404)


def test_fetch_wikipedia_image_success(tmp_path, monkeypatch):
    transport = httpx.MockTransport(_handler)
    monkeypatch.setattr(
        "deckgen_mcp.local.image_wikipedia._client", httpx.Client(transport=transport)
    )
    monkeypatch.setattr("deckgen_mcp.local.image_fetch._client", httpx.Client(transport=transport))

    result = fetch_wikipedia_image("Japan", tmp_path)
    assert result is not None
    assert Path(result["filename"]).exists()
    assert "Public domain" in result["license"]
    assert "Japan" in result["source_url"] or "Flag_of_Japan" in result["source_url"]


def test_fetch_wikipedia_image_missing_returns_none(tmp_path, monkeypatch):
    transport = httpx.MockTransport(_handler)
    monkeypatch.setattr(
        "deckgen_mcp.local.image_wikipedia._client", httpx.Client(transport=transport)
    )

    assert fetch_wikipedia_image("Nonexistent", tmp_path) is None
