from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from mochi_tools_mcp.local.image_fetch import fetch_image

log = logging.getLogger(__name__)
_client = httpx.Client(timeout=15.0, follow_redirects=True)

WIKI_API = "https://en.wikipedia.org/w/api.php"


def fetch_wikipedia_image(query: str, dest_dir: Path) -> dict[str, Any] | None:
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageimages|imageinfo",
        "iiprop": "url|extmetadata",
        "piprop": "thumbnail|name",
        "pithumbsize": "1024",
        "titles": query,
        "redirects": "1",
    }
    try:
        r = _client.get(WIKI_API, params=params)
        r.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("wikipedia query failed for %s: %s", query, e)
        return None

    pages: dict[str, Any] = r.json().get("query", {}).get("pages", {})
    page: dict[str, Any] = next(iter(pages.values()), {})
    if page.get("missing") == "" or "thumbnail" not in page:
        return None

    image_url = page["thumbnail"]["source"]
    metadata = (page.get("imageinfo") or [{}])[0].get("extmetadata", {})
    attribution = metadata.get("Artist", {}).get("value", "Wikipedia")
    license_name = metadata.get("LicenseShortName", {}).get("value", "unknown")

    downloaded = fetch_image(image_url, dest_dir)
    if downloaded is None:
        return None
    return {
        "filename": str(downloaded),
        "source_url": image_url,
        "attribution": attribution,
        "license": license_name,
    }
