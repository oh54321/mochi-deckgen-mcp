import base64
import io
from pathlib import Path

from PIL import Image

from mochi_tools_mcp.local.image_import import import_image


def _png(size=(50, 50)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (0, 255, 0)).save(buf, format="PNG")
    return buf.getvalue()


def test_import_from_file_path(tmp_path: Path):
    src = tmp_path / "input.png"
    src.write_bytes(_png())
    dest = tmp_path / "deck-imgs"
    out = import_image(dest, file_path=src)
    assert out is not None
    assert Path(out).exists()


def test_import_from_base64(tmp_path: Path):
    b64 = base64.b64encode(_png()).decode()
    out = import_image(tmp_path / "deck-imgs", base64_data=b64, filename="hello.png")
    assert out is not None
    assert Path(out).suffix == ".png"


def test_import_requires_input(tmp_path: Path):
    import pytest

    with pytest.raises(ValueError):
        import_image(tmp_path)
