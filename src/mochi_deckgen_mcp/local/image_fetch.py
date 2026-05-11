from __future__ import annotations

import hashlib
import io
import logging
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image

log = logging.getLogger(__name__)
_client = httpx.Client(timeout=15.0, follow_redirects=True)

EXT_BY_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

MAX_EDGE_DEFAULT = 1024


def _svg_to_png(svg_bytes: bytes) -> bytes | None:
    try:
        import cairosvg
    except ImportError:
        log.warning(
            "cairosvg not installed; cannot convert SVG. "
            "Install with 'pip install mochi-deckgen-mcp[svg]'."
        )
        return None
    return cairosvg.svg2png(bytestring=svg_bytes, output_width=MAX_EDGE_DEFAULT)  # type: ignore[no-any-return]


def _process(content: bytes, content_type: str, max_edge_px: int) -> tuple[bytes, str]:
    if content_type == "image/svg+xml":
        png = _svg_to_png(content)
        if png is None:
            return content, ".svg"
        content = png
        content_type = "image/png"

    force_png = content_type == "image/png"
    img: Image.Image = Image.open(io.BytesIO(content))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGBA")
        force_png = True
    else:
        img = img.convert("RGB")

    if max(img.size) > max_edge_px:
        ratio = max_edge_px / max(img.size)
        img = img.resize(
            (int(img.size[0] * ratio), int(img.size[1] * ratio)),
            Image.Resampling.LANCZOS,
        )

    fmt = "PNG" if force_png else "JPEG"
    out = io.BytesIO()
    img.save(out, format=fmt)
    ext = ".png" if fmt == "PNG" else ".jpg"
    return out.getvalue(), ext


def fetch_image(url: str, dest_dir: Path, max_edge_px: int = MAX_EDGE_DEFAULT) -> Path | None:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        r = _client.get(url)
        r.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("image fetch failed %s: %s", url, e)
        return None

    content_type = r.headers.get("content-type", "").split(";")[0].strip()
    if content_type not in EXT_BY_TYPE:
        guess = mimetypes.guess_extension(content_type) or Path(urlparse(url).path).suffix
        if guess in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
            _map = {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "gif": "image/gif",
                "webp": "image/webp",
                "svg": "image/svg+xml",
            }
            content_type = _map[guess.lstrip(".")]
        else:
            log.warning("unknown image content-type for %s", url)
            return None

    try:
        processed, ext = _process(r.content, content_type, max_edge_px)
    except Exception as e:
        log.warning("image processing failed for %s: %s", url, e)
        return None

    digest = hashlib.sha1(processed).hexdigest()[:12]
    out = dest_dir / f"{digest}{ext}"
    if not out.exists():
        out.write_bytes(processed)
    return out
