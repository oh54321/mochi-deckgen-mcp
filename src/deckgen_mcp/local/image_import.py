from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path

from PIL import Image

from deckgen_mcp.local.image_fetch import MAX_EDGE_DEFAULT

_PNG_SIG = b"\x89PNG"


def _process(content: bytes, max_edge_px: int) -> tuple[bytes, str]:
    is_png = content[:4] == _PNG_SIG
    img = Image.open(io.BytesIO(content))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGBA")
        is_png = True
    else:
        img = img.convert("RGB")

    if max(img.size) > max_edge_px:
        ratio = max_edge_px / max(img.size)
        img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)

    fmt = "PNG" if is_png else "JPEG"
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue(), ".png" if fmt == "PNG" else ".jpg"


def import_image(
    dest_dir: Path,
    file_path: Path | None = None,
    base64_data: str | None = None,
    filename: str | None = None,
    max_edge_px: int = MAX_EDGE_DEFAULT,
) -> str | None:
    if file_path is None and base64_data is None:
        raise ValueError("Provide either file_path or base64_data")
    if file_path is not None:
        content = Path(file_path).read_bytes()
    else:
        assert base64_data is not None
        content = base64.b64decode(base64_data)

    processed, ext = _process(content, max_edge_px)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(processed).hexdigest()[:12]
    out = dest_dir / f"{digest}{ext}"
    if not out.exists():
        out.write_bytes(processed)
    return str(out)
