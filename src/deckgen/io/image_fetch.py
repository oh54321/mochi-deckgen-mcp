from __future__ import annotations

import hashlib
import logging
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import httpx

log = logging.getLogger(__name__)
_client = httpx.Client(timeout=15.0, follow_redirects=True)

EXT_BY_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}


def fetch_image(url: str, dest_dir: Path) -> Path | None:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        r = _client.get(url)
        r.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("image fetch failed %s: %s", url, e)
        return None

    ext = EXT_BY_TYPE.get(r.headers.get("content-type", "").split(";")[0].strip())
    if ext is None:
        ext = mimetypes.guess_extension(r.headers.get("content-type", "")) or Path(urlparse(url).path).suffix or ".bin"

    digest = hashlib.sha1(r.content).hexdigest()[:12]
    out = dest_dir / f"{digest}{ext}"
    out.write_bytes(r.content)
    return out
