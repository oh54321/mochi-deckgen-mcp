# DeckGen MCP Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `mochi-deckgen-mcp` into a Python MCP server (`mochi-deckgen-mcp`) that exposes Mochi/local primitives, subagent prompts (≤15 lines), and workflow prompts (≤30 lines) to any MCP-capable client. No server-side LLM. Image-first. Atomic-card-enforced.

**Architecture:** Three layers shipped by one MCP server. Layer 1 = pure-Python tools (filesystem, image processing, Mochi HTTP, sync). Layer 2 = subagent markdown prompts surfaced as MCP prompts + resources + `.claude/agents/` for parallel dispatch. Layer 3 = workflow markdown prompts the user invokes by name. Built alongside the old `deckgen` package; old package deleted at the end.

**Tech Stack:** Python ≥3.11, `mcp` (FastMCP API), `httpx`, `pydantic`, `Pillow`, optional `cairosvg`. Dev: `pytest`, `pytest-asyncio`, `ruff`, `mypy`. Stdio transport.

**Spec:** `docs/specs/2026-05-10-mcp-refactor-design.md` (commit `e0a2e63`).

**Build order:** Scaffold → local tools → Mochi client → sync → prompts → server → quality gate → delete old code → verify.

---

## Phase A — Scaffold

### Task 1: Update pyproject.toml for the new package

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mochi-deckgen-mcp"
version = "0.1.0"
description = "MCP server for Mochi flashcard deck generation, modification, and sync"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.2",
    "httpx>=0.27",
    "pydantic>=2.6",
    "Pillow>=10.0",
]

[project.optional-dependencies]
svg = ["cairosvg>=2.7"]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.5",
    "mypy>=1.10",
    "coverage>=7.5",
]

[project.scripts]
mochi-deckgen-mcp = "mochi_deckgen_mcp.server:main"

[tool.hatch.build.targets.wheel]
packages = ["src/mochi_deckgen_mcp"]

[tool.hatch.build]
include = [
    "src/mochi_deckgen_mcp/**/*.py",
    "src/mochi_deckgen_mcp/prompts/**/*.md",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
files = ["src/mochi_deckgen_mcp"]
```

- [ ] **Step 2: Verify package metadata installs**

Run: `pip install -e ".[dev,svg]"`
Expected: installs without resolver errors; `mochi-deckgen-mcp` console script exists.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build: switch project to mochi-deckgen-mcp with mcp+Pillow deps"
```

---

### Task 2: Scaffold the new package directory tree

**Files:**
- Create: `src/mochi_deckgen_mcp/__init__.py`
- Create: `src/mochi_deckgen_mcp/local/__init__.py`
- Create: `src/mochi_deckgen_mcp/mochi/__init__.py`
- Create: `src/mochi_deckgen_mcp/sync/__init__.py`
- Create: `src/mochi_deckgen_mcp/tools/__init__.py`
- Create: `src/mochi_deckgen_mcp/prompts/agents/.gitkeep`
- Create: `src/mochi_deckgen_mcp/prompts/workflows/.gitkeep`
- Create: `.claude/agents/.gitkeep`

- [ ] **Step 1: Create the skeleton**

```bash
mkdir -p src/mochi_deckgen_mcp/{local,mochi,sync,tools,prompts/agents,prompts/workflows}
mkdir -p .claude/agents
touch src/mochi_deckgen_mcp/__init__.py
touch src/mochi_deckgen_mcp/local/__init__.py
touch src/mochi_deckgen_mcp/mochi/__init__.py
touch src/mochi_deckgen_mcp/sync/__init__.py
touch src/mochi_deckgen_mcp/tools/__init__.py
touch src/mochi_deckgen_mcp/prompts/agents/.gitkeep
touch src/mochi_deckgen_mcp/prompts/workflows/.gitkeep
touch .claude/agents/.gitkeep
```

- [ ] **Step 2: Write version into the top-level package**

`src/mochi_deckgen_mcp/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Commit**

```bash
git add src/mochi_deckgen_mcp .claude/agents
git commit -m "scaffold: empty mochi_deckgen_mcp package tree"
```

---

### Task 3: Port `deck_fs.py` (unchanged) into the new package + its test

**Files:**
- Create: `src/mochi_deckgen_mcp/local/deck_fs.py`
- Create: `tests/test_parse_card.py` (rewrite to import from new package — old file stays for now)
- Create: `tests/fixtures_new/sample_deck/` (copy of existing fixture)

- [ ] **Step 1: Copy `deck_fs.py` verbatim into new package**

Copy `src/deckgen/io/deck_fs.py` → `src/mochi_deckgen_mcp/local/deck_fs.py`. No code changes.

```bash
cp src/deckgen/io/deck_fs.py src/mochi_deckgen_mcp/local/deck_fs.py
```

- [ ] **Step 2: Copy the fixture directory**

```bash
mkdir -p tests/fixtures_new
cp -r tests/fixtures/sample_deck tests/fixtures_new/sample_deck
```

- [ ] **Step 3: Write the new test file**

`tests/test_parse_card_new.py`:

```python
from pathlib import Path

import pytest

from mochi_deckgen_mcp.local.deck_fs import Card, read_card, read_deck

FIXTURE = Path(__file__).parent / "fixtures_new" / "sample_deck"


def test_parses_front_back_tags_and_image():
    card = read_card(FIXTURE / "card-001.md")
    assert card.front_md.startswith("What country has this flag?")
    assert "![](images/jp.png)" in card.front_md
    assert card.back_md.startswith("Japan")
    assert card.tags == ["asia", "island-nations"]
    assert card.image_paths == [Path("images/jp.png")]


def test_parses_math_card_no_tags_no_images():
    card = read_card(FIXTURE / "card-002.md")
    assert "\\int_0^1" in card.front_md
    assert card.back_md.strip() == "$\\frac{1}{2}$"
    assert card.tags == []
    assert card.image_paths == []


def test_only_first_dashes_separate_sides():
    card = read_card(FIXTURE / "card-003.md")
    assert "in front body literal" in card.front_md
    assert card.back_md.startswith("Back")
    assert card.tags == ["edge-case"]


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_card(FIXTURE / "does-not-exist.md")


def test_read_deck_returns_all_cards():
    deck = read_deck(FIXTURE)
    assert deck.name
    assert len(deck.cards) == 3
```

- [ ] **Step 4: Run the new test**

Run: `pytest tests/test_parse_card_new.py -v`
Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/local/deck_fs.py tests/test_parse_card_new.py tests/fixtures_new
git commit -m "port: deck_fs.py and sample_deck fixture into mochi_deckgen_mcp"
```

---

## Phase B — Local tools

### Task 4: Layer-1 `local/malformed_check.py` (pure regex)

**Files:**
- Create: `src/mochi_deckgen_mcp/local/malformed_check.py`
- Create: `tests/test_malformed_check.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_malformed_check.py`:

```python
from pathlib import Path

from mochi_deckgen_mcp.local.malformed_check import check_card_text


def test_well_formed_card():
    text = "What is 2+2?\n\n---\n\n4\n"
    result = check_card_text(text)
    assert result["valid"] is True
    assert result["problems"] == []


def test_missing_separator():
    text = "What is 2+2?\n\n4\n"
    result = check_card_text(text)
    assert result["valid"] is False
    assert "separator" in result["problems"][0].lower()


def test_empty_front():
    text = "\n---\n\n4\n"
    result = check_card_text(text)
    assert result["valid"] is False
    assert any("front" in p.lower() for p in result["problems"])


def test_empty_back():
    text = "What is 2+2?\n\n---\n\n\n"
    result = check_card_text(text)
    assert result["valid"] is False
    assert any("back" in p.lower() for p in result["problems"])


def test_multiple_separators_is_warning_not_error():
    text = "Q\n\n---\n\nA1\n\n---\n\nA2\n"
    result = check_card_text(text)
    assert result["valid"] is True
    assert any("separator" in p.lower() for p in result["problems"])


def test_check_file(tmp_path: Path):
    p = tmp_path / "card-001.md"
    p.write_text("Q\n\n---\n\nA\n")
    from mochi_deckgen_mcp.local.malformed_check import check_card_file

    assert check_card_file(p)["valid"] is True
```

- [ ] **Step 2: Run the tests; confirm import fails**

Run: `pytest tests/test_malformed_check.py -v`
Expected: ModuleNotFoundError on `mochi_deckgen_mcp.local.malformed_check`.

- [ ] **Step 3: Implement `malformed_check.py`**

`src/mochi_deckgen_mcp/local/malformed_check.py`:

```python
from __future__ import annotations

import re
from pathlib import Path

SEPARATOR_RE = re.compile(r"(?m)^---\s*\n\s*\n")


def check_card_text(text: str) -> dict:
    problems: list[str] = []
    matches = list(SEPARATOR_RE.finditer(text))
    if not matches:
        problems.append("Missing front/back separator (blank line + --- + blank line).")
        return {"valid": False, "problems": problems}

    if len(matches) > 1:
        problems.append("Multiple separators found; only the first is used.")

    front = text[: matches[0].start()].strip()
    back = text[matches[0].end() :].strip()
    if not front:
        problems.append("Empty front.")
    if not back:
        problems.append("Empty back.")

    valid = not any(p.startswith(("Empty", "Missing")) for p in problems)
    return {"valid": valid, "problems": problems}


def check_card_file(path: Path) -> dict:
    return check_card_text(Path(path).read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run tests; confirm pass**

Run: `pytest tests/test_malformed_check.py -v`
Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/local/malformed_check.py tests/test_malformed_check.py
git commit -m "feat: local/malformed_check structural validator (Layer-1, pure regex)"
```

---

### Task 5: Extend `local/image_fetch.py` — resize, EXIF strip, dedup, SVG→PNG

**Files:**
- Create: `src/mochi_deckgen_mcp/local/image_fetch.py`
- Create: `tests/test_image_fetch.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_image_fetch.py`:

```python
import io
from pathlib import Path

import httpx
import pytest
from PIL import Image

from mochi_deckgen_mcp.local.image_fetch import fetch_image


def _png_bytes(size=(2000, 1500), color=(255, 0, 0)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_fetch_resizes_to_max_edge(tmp_path, monkeypatch):
    transport = httpx.MockTransport(lambda r: httpx.Response(200, content=_png_bytes(), headers={"content-type": "image/png"}))
    monkeypatch.setattr("mochi_deckgen_mcp.local.image_fetch._client", httpx.Client(transport=transport))

    out = fetch_image("https://x/y.png", tmp_path, max_edge_px=512)
    assert out is not None
    img = Image.open(out)
    assert max(img.size) == 512


def test_fetch_dedups_by_content_hash(tmp_path, monkeypatch):
    content = _png_bytes()
    transport = httpx.MockTransport(lambda r: httpx.Response(200, content=content, headers={"content-type": "image/png"}))
    monkeypatch.setattr("mochi_deckgen_mcp.local.image_fetch._client", httpx.Client(transport=transport))

    a = fetch_image("https://x/a.png", tmp_path)
    b = fetch_image("https://x/b.png", tmp_path)
    assert a == b  # same filename due to content hash


def test_fetch_returns_none_on_http_error(tmp_path, monkeypatch):
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    monkeypatch.setattr("mochi_deckgen_mcp.local.image_fetch._client", httpx.Client(transport=transport))

    assert fetch_image("https://x/y.png", tmp_path) is None


def test_svg_conversion_when_cairosvg_present(tmp_path, monkeypatch):
    pytest.importorskip("cairosvg")
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>'
    transport = httpx.MockTransport(lambda r: httpx.Response(200, content=svg, headers={"content-type": "image/svg+xml"}))
    monkeypatch.setattr("mochi_deckgen_mcp.local.image_fetch._client", httpx.Client(transport=transport))

    out = fetch_image("https://x/y.svg", tmp_path)
    assert out is not None
    assert out.suffix == ".png"
    assert Image.open(out).size[0] > 0
```

- [ ] **Step 2: Run tests; confirm failure (module missing)**

Run: `pytest tests/test_image_fetch.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `image_fetch.py`**

`src/mochi_deckgen_mcp/local/image_fetch.py`:

```python
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
        log.warning("cairosvg not installed; cannot convert SVG. Install with 'pip install mochi-deckgen-mcp[svg]'.")
        return None
    return cairosvg.svg2png(bytestring=svg_bytes, output_width=MAX_EDGE_DEFAULT)


def _process(content: bytes, content_type: str, max_edge_px: int) -> tuple[bytes, str]:
    if content_type == "image/svg+xml":
        png = _svg_to_png(content)
        if png is None:
            return content, ".svg"
        content = png
        content_type = "image/png"

    img = Image.open(io.BytesIO(content))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    if max(img.size) > max_edge_px:
        ratio = max_edge_px / max(img.size)
        img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)

    fmt = "PNG" if img.mode == "RGBA" else "JPEG"
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
            content_type = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                            "gif": "image/gif", "webp": "image/webp", "svg": "image/svg+xml"}[guess.lstrip(".")]
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_image_fetch.py -v`
Expected: 4 tests pass (or 3 + 1 skip if cairosvg not installed).

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/local/image_fetch.py tests/test_image_fetch.py
git commit -m "feat: image_fetch with resize, dedup, SVG→PNG, EXIF strip"
```

---

### Task 6: `local/image_wikipedia.py` — Wikipedia Commons fetcher

**Files:**
- Create: `src/mochi_deckgen_mcp/local/image_wikipedia.py`
- Create: `tests/test_image_wikipedia.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_image_wikipedia.py`:

```python
from pathlib import Path

import httpx
import pytest

from mochi_deckgen_mcp.local.image_wikipedia import fetch_wikipedia_image


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "action=query" in url and "Japan" in url:
        return httpx.Response(200, json={
            "query": {
                "pages": {
                    "1": {
                        "title": "Japan",
                        "thumbnail": {"source": "https://upload.wikimedia.org/Flag_of_Japan.png", "width": 800},
                        "pageimage": "Flag_of_Japan.png",
                        "imageinfo": [{
                            "url": "https://upload.wikimedia.org/Flag_of_Japan.png",
                            "extmetadata": {
                                "Artist": {"value": "Government of Japan"},
                                "LicenseShortName": {"value": "Public domain"},
                            },
                        }],
                    }
                }
            }
        })
    if url.endswith("Flag_of_Japan.png"):
        import io as _io
        from PIL import Image as _Image
        buf = _io.BytesIO()
        _Image.new("RGB", (100, 60), (255, 0, 0)).save(buf, format="PNG")
        return httpx.Response(200, content=buf.getvalue(), headers={"content-type": "image/png"})
    if "Nonexistent" in url:
        return httpx.Response(200, json={"query": {"pages": {"-1": {"missing": ""}}}})
    return httpx.Response(404)


def test_fetch_wikipedia_image_success(tmp_path, monkeypatch):
    transport = httpx.MockTransport(_handler)
    monkeypatch.setattr("mochi_deckgen_mcp.local.image_wikipedia._client", httpx.Client(transport=transport))
    monkeypatch.setattr("mochi_deckgen_mcp.local.image_fetch._client", httpx.Client(transport=transport))

    result = fetch_wikipedia_image("Japan", tmp_path)
    assert result is not None
    assert Path(result["filename"]).exists()
    assert "Public domain" in result["license"]
    assert "Japan" in result["source_url"] or "Flag_of_Japan" in result["source_url"]


def test_fetch_wikipedia_image_missing_returns_none(tmp_path, monkeypatch):
    transport = httpx.MockTransport(_handler)
    monkeypatch.setattr("mochi_deckgen_mcp.local.image_wikipedia._client", httpx.Client(transport=transport))

    assert fetch_wikipedia_image("Nonexistent", tmp_path) is None
```

- [ ] **Step 2: Run tests; expect failure**

Run: `pytest tests/test_image_wikipedia.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `image_wikipedia.py`**

`src/mochi_deckgen_mcp/local/image_wikipedia.py`:

```python
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from mochi_deckgen_mcp.local.image_fetch import fetch_image

log = logging.getLogger(__name__)
_client = httpx.Client(timeout=15.0, follow_redirects=True)

WIKI_API = "https://en.wikipedia.org/w/api.php"


def fetch_wikipedia_image(query: str, dest_dir: Path) -> dict | None:
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

    pages = r.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_image_wikipedia.py -v`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/local/image_wikipedia.py tests/test_image_wikipedia.py
git commit -m "feat: Wikipedia Commons image fetcher via MediaWiki API"
```

---

### Task 7: `local/image_import.py` — user-supplied images

**Files:**
- Create: `src/mochi_deckgen_mcp/local/image_import.py`
- Create: `tests/test_image_import.py`

- [ ] **Step 1: Write failing tests**

`tests/test_image_import.py`:

```python
import base64
import io
from pathlib import Path

from PIL import Image

from mochi_deckgen_mcp.local.image_import import import_image


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
```

- [ ] **Step 2: Run; expect failure**

Run: `pytest tests/test_image_import.py -v`

- [ ] **Step 3: Implement**

`src/mochi_deckgen_mcp/local/image_import.py`:

```python
from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path

from PIL import Image

from mochi_deckgen_mcp.local.image_fetch import MAX_EDGE_DEFAULT


def _process(content: bytes, max_edge_px: int) -> tuple[bytes, str]:
    img = Image.open(io.BytesIO(content))
    img = img.convert("RGBA" if img.mode in ("RGBA", "P") else "RGB")
    if max(img.size) > max_edge_px:
        ratio = max_edge_px / max(img.size)
        img = img.resize((int(img.size[0] * ratio), int(img.size[1] * ratio)), Image.LANCZOS)
    fmt = "PNG" if img.mode == "RGBA" else "JPEG"
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_image_import.py -v`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/local/image_import.py tests/test_image_import.py
git commit -m "feat: user-supplied image import (file path or base64)"
```

---

### Task 8: Local deck CRUD primitives — `local/deck_ops.py`

**Files:**
- Create: `src/mochi_deckgen_mcp/local/deck_ops.py`
- Create: `tests/test_deck_ops.py`

- [ ] **Step 1: Write failing tests**

`tests/test_deck_ops.py`:

```python
from pathlib import Path

import pytest

from mochi_deckgen_mcp.local.deck_ops import (
    create_deck, write_card, read_card, list_decks, list_cards,
    delete_card, delete_deck,
)


def test_create_deck_writes_metadata(tmp_path: Path):
    info = create_deck(tmp_path, "Flags", description="World flags")
    assert (tmp_path / "raw" / "Flags" / "deck.json").exists()
    assert info["name"] == "Flags"


def test_write_and_read_card(tmp_path: Path):
    create_deck(tmp_path, "T")
    p = write_card(tmp_path, "T", 1, "Front?", "Back", tags=["x"])
    card = read_card(tmp_path, "T", 1)
    assert card["front_md"] == "Front?"
    assert card["back_md"] == "Back"
    assert card["tags"] == ["x"]
    assert Path(p).exists()


def test_list_cards_and_decks(tmp_path: Path):
    create_deck(tmp_path, "A")
    write_card(tmp_path, "A", 1, "Q1", "A1")
    write_card(tmp_path, "A", 2, "Q2", "A2")
    decks = list_decks(tmp_path)
    assert any(d["name"] == "A" and d["card_count"] == 2 for d in decks)
    cards = list_cards(tmp_path, "A")
    assert len(cards) == 2
    assert cards[0]["index"] == 1


def test_delete_card_soft_moves_to_trash(tmp_path: Path):
    create_deck(tmp_path, "A")
    write_card(tmp_path, "A", 1, "Q", "A")
    delete_card(tmp_path, "A", 1)
    assert not (tmp_path / "raw" / "A" / "card-001.md").exists()
    trashed = list((tmp_path / ".trash").rglob("card-001.md"))
    assert len(trashed) == 1


def test_delete_deck_soft_moves_folder(tmp_path: Path):
    create_deck(tmp_path, "A")
    delete_deck(tmp_path, "A")
    assert not (tmp_path / "raw" / "A").exists()
    assert any((tmp_path / ".trash").iterdir())


def test_create_deck_refuses_overwrite(tmp_path: Path):
    create_deck(tmp_path, "Z")
    with pytest.raises(FileExistsError):
        create_deck(tmp_path, "Z")
```

- [ ] **Step 2: Run; expect failure**

Run: `pytest tests/test_deck_ops.py -v`

- [ ] **Step 3: Implement `deck_ops.py`**

`src/mochi_deckgen_mcp/local/deck_ops.py`:

```python
from __future__ import annotations

import datetime as _dt
import json
import shutil
from pathlib import Path

from mochi_deckgen_mcp.local.deck_fs import read_card as _read_card_file

CARD_PAT = "card-{i:03d}.md"


def _decks_root(root: Path) -> Path:
    return Path(root)


def _raw(root: Path) -> Path:
    return _decks_root(root) / "raw"


def _trash(root: Path) -> Path:
    return _decks_root(root) / ".trash"


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat().replace("+00:00", "Z")


def create_deck(root: Path, name: str, description: str = "", parent_name: str | None = None) -> dict:
    folder = _raw(root) / name
    if folder.exists():
        raise FileExistsError(f"Deck {name} already exists at {folder}")
    folder.mkdir(parents=True)
    meta = {
        "name": name,
        "description": description,
        "parent_name": parent_name,
        "created_at": _now(),
    }
    (folder / "deck.json").write_text(json.dumps(meta, indent=2))
    return meta


def write_card(
    root: Path, deck: str, index: int, front_md: str, back_md: str,
    tags: list[str] | None = None, image_filename: str | None = None,
) -> str:
    folder = _raw(root) / deck
    if not folder.exists():
        raise FileNotFoundError(f"Deck {deck} does not exist")
    body = front_md
    if image_filename and f"]({image_filename})" not in body:
        body = f"![]({image_filename})\n\n{body}"
    body += f"\n\n---\n\n{back_md}"
    if tags:
        body += "\n\nTags: " + " ".join(f"#{t}" for t in tags)
    body += "\n"
    p = folder / CARD_PAT.format(i=index)
    p.write_text(body, encoding="utf-8")
    return str(p)


def read_card(root: Path, deck: str, index: int) -> dict:
    p = _raw(root) / deck / CARD_PAT.format(i=index)
    c = _read_card_file(p)
    return {
        "front_md": c.front_md,
        "back_md": c.back_md,
        "tags": c.tags,
        "image_paths": [str(x) for x in c.image_paths],
        "path": str(p),
    }


def list_decks(root: Path) -> list[dict]:
    raw = _raw(root)
    if not raw.exists():
        return []
    result = []
    for folder in sorted(p for p in raw.iterdir() if p.is_dir()):
        cards = list(folder.glob("card-*.md"))
        has_map = (folder / ".mochi.json").exists()
        result.append({"name": folder.name, "card_count": len(cards), "has_mochi_mapping": has_map})
    return result


def list_cards(root: Path, deck: str) -> list[dict]:
    folder = _raw(root) / deck
    cards = []
    for p in sorted(folder.glob("card-*.md")):
        index = int(p.stem.split("-")[1])
        c = _read_card_file(p)
        first_line = c.front_md.splitlines()[0] if c.front_md else ""
        cards.append({
            "index": index,
            "front_first_line": first_line[:80],
            "tags": c.tags,
        })
    return cards


def _move_to_trash(src: Path, root: Path, sub: str) -> Path:
    trash = _trash(root) / sub / _now().replace(":", "-")
    trash.mkdir(parents=True, exist_ok=True)
    dest = trash / src.name
    shutil.move(str(src), str(dest))
    return dest


def delete_card(root: Path, deck: str, index: int) -> str:
    p = _raw(root) / deck / CARD_PAT.format(i=index)
    return str(_move_to_trash(p, root, deck))


def delete_deck(root: Path, deck: str) -> str:
    folder = _raw(root) / deck
    trash = _trash(root)
    trash.mkdir(parents=True, exist_ok=True)
    dest = trash / f"{deck}-{_now().replace(':', '-')}"
    shutil.move(str(folder), str(dest))
    return str(dest)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_deck_ops.py -v`
Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/local/deck_ops.py tests/test_deck_ops.py
git commit -m "feat: local deck CRUD with soft-delete to .trash/"
```

---

### Task 9: Wrap local primitives as MCP tools — `tools/local_tools.py`

**Files:**
- Create: `src/mochi_deckgen_mcp/tools/local_tools.py`
- Create: `src/mochi_deckgen_mcp/config.py`
- Create: `tests/test_local_tools.py`

- [ ] **Step 1: Implement `config.py`**

`src/mochi_deckgen_mcp/config.py`:

```python
from __future__ import annotations

import os
from pathlib import Path


def decks_root() -> Path:
    env = os.environ.get("DECKGEN_DECKS_ROOT")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".local" / "share" / "mochi-deckgen-mcp" / "decks"


def default_regen() -> int:
    return int(os.environ.get("DECKGEN_DEFAULT_REGEN", "1"))


def default_concurrency() -> int:
    return int(os.environ.get("DECKGEN_DEFAULT_CONCURRENCY", "10"))


def mochi_api_key() -> str | None:
    return os.environ.get("MOCHI_API_KEY")
```

- [ ] **Step 2: Write failing tests**

`tests/test_local_tools.py`:

```python
from pathlib import Path

from mochi_deckgen_mcp.tools import local_tools


def test_register_returns_tool_callables():
    tools = local_tools.collect()
    names = {t["name"] for t in tools}
    expected = {
        "local_create_deck", "local_write_card", "local_read_card",
        "local_list_decks", "local_list_cards",
        "local_delete_card", "local_delete_deck",
        "local_fetch_image", "local_fetch_wikipedia_image",
        "local_import_image", "local_check_malformed",
    }
    assert expected <= names


def test_local_create_and_write_via_tool(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DECKGEN_DECKS_ROOT", str(tmp_path))
    tools = {t["name"]: t["fn"] for t in local_tools.collect()}
    tools["local_create_deck"](name="T")
    tools["local_write_card"](deck="T", index=1, front_md="Q", back_md="A")
    cards = tools["local_list_cards"](deck="T")
    assert len(cards) == 1
```

- [ ] **Step 3: Run; expect failure**

Run: `pytest tests/test_local_tools.py -v`

- [ ] **Step 4: Implement `tools/local_tools.py`**

`src/mochi_deckgen_mcp/tools/local_tools.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from mochi_deckgen_mcp.config import decks_root
from mochi_deckgen_mcp.local import deck_ops, image_fetch, image_import, image_wikipedia, malformed_check


def _t(name: str, fn: Callable[..., Any], description: str) -> dict:
    return {"name": name, "fn": fn, "description": description}


def collect() -> list[dict]:
    root = decks_root

    def local_create_deck(name: str, description: str = "", parent_name: str | None = None) -> dict:
        return deck_ops.create_deck(root(), name, description, parent_name)

    def local_write_card(
        deck: str, index: int, front_md: str, back_md: str,
        tags: list[str] | None = None, image_filename: str | None = None,
    ) -> dict:
        path = deck_ops.write_card(root(), deck, index, front_md, back_md, tags, image_filename)
        return {"path": path}

    def local_read_card(deck: str, index: int) -> dict:
        return deck_ops.read_card(root(), deck, index)

    def local_list_decks() -> list[dict]:
        return deck_ops.list_decks(root())

    def local_list_cards(deck: str) -> list[dict]:
        return deck_ops.list_cards(root(), deck)

    def local_delete_card(deck: str, index: int) -> dict:
        return {"trashed_to": deck_ops.delete_card(root(), deck, index)}

    def local_delete_deck(name: str) -> dict:
        return {"trashed_to": deck_ops.delete_deck(root(), name)}

    def local_fetch_image(url: str, deck: str, max_edge_px: int = 1024) -> dict:
        dest = root() / "raw" / deck / "images"
        p = image_fetch.fetch_image(url, dest, max_edge_px)
        return {"path": str(p) if p else None}

    def local_fetch_wikipedia_image(query: str, deck: str) -> dict | None:
        dest = root() / "raw" / deck / "images"
        return image_wikipedia.fetch_wikipedia_image(query, dest)

    def local_import_image(
        deck: str, file_path: str | None = None, base64_data: str | None = None, filename: str | None = None,
    ) -> dict:
        dest = root() / "raw" / deck / "images"
        p = image_import.import_image(
            dest,
            file_path=Path(file_path) if file_path else None,
            base64_data=base64_data,
            filename=filename,
        )
        return {"path": p}

    def local_check_malformed(deck: str, index: int | None = None) -> Any:
        folder = root() / "raw" / deck
        if index is not None:
            return malformed_check.check_card_file(folder / f"card-{index:03d}.md")
        results = {}
        for p in sorted(folder.glob("card-*.md")):
            i = int(p.stem.split("-")[1])
            results[i] = malformed_check.check_card_file(p)
        return results

    return [
        _t("local_create_deck", local_create_deck, "Create a new local deck folder."),
        _t("local_write_card", local_write_card, "Write a card to a local deck."),
        _t("local_read_card", local_read_card, "Read a card from a local deck."),
        _t("local_list_decks", local_list_decks, "List local decks."),
        _t("local_list_cards", local_list_cards, "List cards in a local deck."),
        _t("local_delete_card", local_delete_card, "Soft-delete a card (move to .trash/)."),
        _t("local_delete_deck", local_delete_deck, "Soft-delete a deck (move to .trash/)."),
        _t("local_fetch_image", local_fetch_image, "Download, process, dedup an image into a deck."),
        _t("local_fetch_wikipedia_image", local_fetch_wikipedia_image, "Fetch an image from Wikipedia Commons."),
        _t("local_import_image", local_import_image, "Import a user-supplied image."),
        _t("local_check_malformed", local_check_malformed, "Regex-only structural check of cards."),
    ]
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_local_tools.py -v`
Expected: 2 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/mochi_deckgen_mcp/config.py src/mochi_deckgen_mcp/tools/local_tools.py tests/test_local_tools.py
git commit -m "feat: tools/local_tools wraps local primitives for MCP"
```

---

## Phase C — Mochi client

### Task 10: Mochi error types + pydantic schemas

**Files:**
- Create: `src/mochi_deckgen_mcp/mochi/errors.py`
- Create: `src/mochi_deckgen_mcp/mochi/schemas.py`

- [ ] **Step 1: Write `errors.py`**

`src/mochi_deckgen_mcp/mochi/errors.py`:

```python
from __future__ import annotations


class MochiError(Exception):
    pass


class MochiAuthError(MochiError):
    pass


class MochiNotFoundError(MochiError):
    pass


class MochiRateLimitError(MochiError):
    pass


class MochiServerError(MochiError):
    pass
```

- [ ] **Step 2: Write `schemas.py`**

`src/mochi_deckgen_mcp/mochi/schemas.py`:

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Deck(BaseModel):
    id: str
    name: str
    parent_id: str | None = Field(default=None, alias="parent-id")
    trashed: str | None = Field(default=None, alias="trashed?")

    model_config = {"populate_by_name": True}


class Card(BaseModel):
    id: str
    content: str
    deck_id: str = Field(alias="deck-id")
    template_id: str | None = Field(default=None, alias="template-id")
    fields: dict[str, Any] = Field(default_factory=dict)
    trashed: str | None = Field(default=None, alias="trashed?")

    model_config = {"populate_by_name": True}


class Template(BaseModel):
    id: str
    name: str
    content: str
    fields: dict[str, Any] = Field(default_factory=dict)


class ListResponse(BaseModel):
    docs: list[dict]
    bookmark: str | None = None
```

- [ ] **Step 3: Commit**

```bash
git add src/mochi_deckgen_mcp/mochi/errors.py src/mochi_deckgen_mcp/mochi/schemas.py
git commit -m "feat: mochi error types and pydantic schemas"
```

---

### Task 11: Mochi HTTP client with retry — `mochi/client.py`

**Files:**
- Create: `src/mochi_deckgen_mcp/mochi/client.py`
- Create: `tests/test_mochi_client.py`

- [ ] **Step 1: Write failing tests**

`tests/test_mochi_client.py`:

```python
import httpx
import pytest

from mochi_deckgen_mcp.mochi.client import MochiClient
from mochi_deckgen_mcp.mochi.errors import MochiAuthError, MochiNotFoundError


def _client(handler):
    transport = httpx.MockTransport(handler)
    return MochiClient(api_key="k", _transport=transport)


def test_list_decks(monkeypatch):
    def h(r):
        return httpx.Response(200, json={"docs": [{"id": "d1", "name": "Flags"}], "bookmark": None})

    c = _client(h)
    decks = c.list_decks()
    assert decks["docs"][0]["name"] == "Flags"


def test_get_card_404():
    def h(r):
        return httpx.Response(404, json={"error": "not found"})

    c = _client(h)
    with pytest.raises(MochiNotFoundError):
        c.get_card("missing")


def test_401_raises_auth():
    def h(r):
        return httpx.Response(401)

    c = _client(h)
    with pytest.raises(MochiAuthError):
        c.list_decks()


def test_429_retries_then_succeeds():
    calls = {"n": 0}

    def h(r):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json={"docs": [], "bookmark": None})

    c = _client(h)
    c.list_decks()
    assert calls["n"] == 3


def test_create_card_posts_json():
    captured = {}

    def h(r):
        captured["body"] = r.read().decode()
        return httpx.Response(200, json={"id": "c1", "content": "Q\n---\nA", "deck-id": "d1"})

    c = _client(h)
    out = c.create_card(deck_id="d1", content="Q\n---\nA")
    assert out["id"] == "c1"
    assert "deck-id" in captured["body"]
```

- [ ] **Step 2: Run; expect failure**

Run: `pytest tests/test_mochi_client.py -v`

- [ ] **Step 3: Implement `mochi/client.py`**

`src/mochi_deckgen_mcp/mochi/client.py`:

```python
from __future__ import annotations

import time
from typing import Any

import httpx

from mochi_deckgen_mcp.mochi.errors import (
    MochiAuthError, MochiError, MochiNotFoundError, MochiRateLimitError, MochiServerError,
)

BASE_URL = "https://app.mochi.cards/api"
MAX_RETRIES = 5


class MochiClient:
    def __init__(self, api_key: str, _transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(
            base_url=BASE_URL,
            auth=(api_key, ""),
            timeout=30.0,
            transport=_transport,
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        for attempt in range(MAX_RETRIES):
            try:
                r = self._client.request(method, path, **kwargs)
            except httpx.HTTPError as e:
                if attempt + 1 == MAX_RETRIES:
                    raise MochiError(f"transport error: {e}") from e
                time.sleep(min(2 ** attempt * 0.1, 5))
                continue

            if r.status_code == 401:
                raise MochiAuthError("Invalid MOCHI_API_KEY")
            if r.status_code == 404:
                raise MochiNotFoundError(f"Not found: {method} {path}")
            if r.status_code == 429 or 500 <= r.status_code < 600:
                if attempt + 1 == MAX_RETRIES:
                    if r.status_code == 429:
                        raise MochiRateLimitError("Mochi rate-limited after retries")
                    raise MochiServerError(f"Mochi {r.status_code}")
                time.sleep(min(2 ** attempt * 0.1, 5))
                continue
            r.raise_for_status()
            return r.json() if r.content else {}
        raise MochiError("unreachable")

    # decks
    def list_decks(self, bookmark: str | None = None) -> dict:
        params = {"bookmark": bookmark} if bookmark else {}
        return self._request("GET", "/decks/", params=params)

    def get_deck(self, deck_id: str) -> dict:
        return self._request("GET", f"/decks/{deck_id}")

    def create_deck(self, name: str, parent_id: str | None = None) -> dict:
        body = {"name": name}
        if parent_id:
            body["parent-id"] = parent_id
        return self._request("POST", "/decks/", json=body)

    def update_deck(self, deck_id: str, **fields: Any) -> dict:
        return self._request("POST", f"/decks/{deck_id}", json=fields)

    def delete_deck(self, deck_id: str) -> dict:
        return self._request("DELETE", f"/decks/{deck_id}")

    def trash_deck(self, deck_id: str, iso_timestamp: str) -> dict:
        return self.update_deck(deck_id, **{"trashed?": iso_timestamp})

    # cards
    def list_cards(self, deck_id: str | None = None, bookmark: str | None = None) -> dict:
        params: dict[str, str] = {}
        if deck_id:
            params["deck-id"] = deck_id
        if bookmark:
            params["bookmark"] = bookmark
        return self._request("GET", "/cards/", params=params)

    def get_card(self, card_id: str) -> dict:
        return self._request("GET", f"/cards/{card_id}")

    def create_card(self, deck_id: str, content: str, template_id: str | None = None, fields: dict | None = None) -> dict:
        body: dict = {"deck-id": deck_id, "content": content}
        if template_id:
            body["template-id"] = template_id
        if fields:
            body["fields"] = fields
        return self._request("POST", "/cards/", json=body)

    def update_card(self, card_id: str, **fields: Any) -> dict:
        return self._request("POST", f"/cards/{card_id}", json=fields)

    def delete_card(self, card_id: str) -> dict:
        return self._request("DELETE", f"/cards/{card_id}")

    def trash_card(self, card_id: str, iso_timestamp: str) -> dict:
        return self.update_card(card_id, **{"trashed?": iso_timestamp})

    def add_attachment(self, card_id: str, filename: str, content: bytes, content_type: str) -> dict:
        files = {"file": (filename, content, content_type)}
        return self._request("POST", f"/cards/{card_id}/attachments/{filename}", files=files)

    def delete_attachment(self, card_id: str, filename: str) -> dict:
        return self._request("DELETE", f"/cards/{card_id}/attachments/{filename}")

    # templates
    def list_templates(self) -> dict:
        return self._request("GET", "/templates/")

    def get_template(self, template_id: str) -> dict:
        return self._request("GET", f"/templates/{template_id}")

    def create_template(self, name: str, content: str, fields: dict | None = None) -> dict:
        body: dict = {"name": name, "content": content}
        if fields:
            body["fields"] = fields
        return self._request("POST", "/templates/", json=body)

    def get_due_cards(self, deck_id: str | None = None) -> dict:
        path = f"/due/{deck_id}" if deck_id else "/due"
        return self._request("GET", path)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_mochi_client.py -v`
Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/mochi/client.py tests/test_mochi_client.py
git commit -m "feat: Mochi API client with auth, retry, full CRUD"
```

---

### Task 12: `tools/mochi_tools.py` — wrap MochiClient as MCP tools

**Files:**
- Create: `src/mochi_deckgen_mcp/tools/mochi_tools.py`
- Create: `tests/test_mochi_tools.py`

- [ ] **Step 1: Write failing tests**

`tests/test_mochi_tools.py`:

```python
import httpx
import pytest

from mochi_deckgen_mcp.tools import mochi_tools


def test_collect_with_no_key_returns_error_stubs(monkeypatch):
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    tools = mochi_tools.collect()
    names = {t["name"] for t in tools}
    assert "mochi_list_decks" in names

    fn = next(t["fn"] for t in tools if t["name"] == "mochi_list_decks")
    out = fn()
    assert out.get("isError") is True
    assert "MOCHI_API_KEY" in out["content"][0]["text"]


def test_full_coverage_of_endpoints(monkeypatch):
    monkeypatch.setenv("MOCHI_API_KEY", "k")
    tools = mochi_tools.collect()
    names = {t["name"] for t in tools}
    expected = {
        "mochi_list_decks", "mochi_get_deck", "mochi_create_deck", "mochi_update_deck",
        "mochi_delete_deck", "mochi_trash_deck",
        "mochi_list_cards", "mochi_get_card", "mochi_create_card", "mochi_update_card",
        "mochi_delete_card", "mochi_trash_card",
        "mochi_add_attachment", "mochi_delete_attachment",
        "mochi_list_templates", "mochi_get_template", "mochi_create_template",
        "mochi_get_due_cards",
    }
    assert expected <= names
```

- [ ] **Step 2: Run; expect failure**

Run: `pytest tests/test_mochi_tools.py -v`

- [ ] **Step 3: Implement `mochi_tools.py`**

`src/mochi_deckgen_mcp/tools/mochi_tools.py`:

```python
from __future__ import annotations

import base64
import datetime as _dt
from typing import Any, Callable

from mochi_deckgen_mcp.config import mochi_api_key
from mochi_deckgen_mcp.mochi.client import MochiClient


_AUTH_HELP = (
    "MOCHI_API_KEY missing. Get a key at https://app.mochi.cards/ → click your avatar → "
    "Account Settings → API Keys, then set MOCHI_API_KEY in your MCP client config."
)


def _err(msg: str) -> dict:
    return {"isError": True, "content": [{"type": "text", "text": msg}]}


def _now() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat().replace("+00:00", "Z")


def _t(name: str, fn: Callable[..., Any], description: str) -> dict:
    return {"name": name, "fn": fn, "description": description}


def collect() -> list[dict]:
    def _client_or_err() -> MochiClient | dict:
        key = mochi_api_key()
        if not key:
            return _err(_AUTH_HELP)
        return MochiClient(api_key=key)

    def wrap(method_name: str) -> Callable[..., Any]:
        def runner(**kwargs: Any) -> Any:
            c = _client_or_err()
            if isinstance(c, dict):
                return c
            return getattr(c, method_name)(**kwargs)
        return runner

    def mochi_trash_deck(deck_id: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.trash_deck(deck_id, _now())

    def mochi_trash_card(card_id: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.trash_card(card_id, _now())

    def mochi_add_attachment(card_id: str, filename: str, base64_content: str, content_type: str) -> Any:
        c = _client_or_err()
        if isinstance(c, dict):
            return c
        return c.add_attachment(card_id, filename, base64.b64decode(base64_content), content_type)

    return [
        _t("mochi_list_decks", wrap("list_decks"), "List Mochi decks."),
        _t("mochi_get_deck", wrap("get_deck"), "Get a Mochi deck by id."),
        _t("mochi_create_deck", wrap("create_deck"), "Create a Mochi deck."),
        _t("mochi_update_deck", wrap("update_deck"), "Update a Mochi deck."),
        _t("mochi_delete_deck", wrap("delete_deck"), "Hard-delete a Mochi deck."),
        _t("mochi_trash_deck", mochi_trash_deck, "Soft-delete (trash) a Mochi deck."),
        _t("mochi_list_cards", wrap("list_cards"), "List Mochi cards."),
        _t("mochi_get_card", wrap("get_card"), "Get a Mochi card by id."),
        _t("mochi_create_card", wrap("create_card"), "Create a Mochi card."),
        _t("mochi_update_card", wrap("update_card"), "Update a Mochi card."),
        _t("mochi_delete_card", wrap("delete_card"), "Hard-delete a Mochi card."),
        _t("mochi_trash_card", mochi_trash_card, "Soft-delete (trash) a Mochi card."),
        _t("mochi_add_attachment", mochi_add_attachment, "Add an attachment to a Mochi card (base64)."),
        _t("mochi_delete_attachment", wrap("delete_attachment"), "Delete an attachment."),
        _t("mochi_list_templates", wrap("list_templates"), "List Mochi templates."),
        _t("mochi_get_template", wrap("get_template"), "Get a Mochi template by id."),
        _t("mochi_create_template", wrap("create_template"), "Create a Mochi template."),
        _t("mochi_get_due_cards", wrap("get_due_cards"), "Get due cards (optionally for one deck)."),
    ]
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_mochi_tools.py -v`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/tools/mochi_tools.py tests/test_mochi_tools.py
git commit -m "feat: tools/mochi_tools wraps MochiClient (full itzcull parity)"
```

---

## Phase D — Sync

### Task 13: `.mochi.json` mapping read/write — `sync/mapping.py`

**Files:**
- Create: `src/mochi_deckgen_mcp/sync/mapping.py`
- Create: `tests/test_sync_mapping.py`

- [ ] **Step 1: Write failing tests**

`tests/test_sync_mapping.py`:

```python
from pathlib import Path

from mochi_deckgen_mcp.sync.mapping import Mapping, load_mapping, save_mapping, hash_text


def test_round_trip(tmp_path: Path):
    folder = tmp_path / "raw" / "Flags"
    folder.mkdir(parents=True)
    m = Mapping(deck_id="d1", deck_name_on_mochi="Flags", parent_id=None, template_id=None)
    m.cards["card-001.md"] = {"id": "c1", "content_hash": "sha1:abc"}
    m.images["images/jp.png"] = "sha1:def"
    save_mapping(folder, m)
    loaded = load_mapping(folder)
    assert loaded is not None
    assert loaded.deck_id == "d1"
    assert loaded.cards["card-001.md"]["id"] == "c1"


def test_missing_returns_none(tmp_path):
    assert load_mapping(tmp_path) is None


def test_hash_text_stable():
    assert hash_text("hello") == hash_text("hello")
    assert hash_text("a").startswith("sha1:")
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `sync/mapping.py`**

`src/mochi_deckgen_mcp/sync/mapping.py`:

```python
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Mapping:
    deck_id: str
    deck_name_on_mochi: str
    parent_id: str | None = None
    template_id: str | None = None
    cards: dict[str, dict] = field(default_factory=dict)
    images: dict[str, str] = field(default_factory=dict)
    last_push_at: str | None = None


def load_mapping(deck_folder: Path) -> Mapping | None:
    p = Path(deck_folder) / ".mochi.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text())
    return Mapping(**data)


def save_mapping(deck_folder: Path, m: Mapping) -> None:
    p = Path(deck_folder) / ".mochi.json"
    p.write_text(json.dumps(m.__dict__, indent=2))


def hash_text(text: str) -> str:
    return "sha1:" + hashlib.sha1(text.encode("utf-8")).hexdigest()


def hash_bytes(data: bytes) -> str:
    return "sha1:" + hashlib.sha1(data).hexdigest()
```

- [ ] **Step 4: Run tests**

Expected: 3 pass.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/sync/mapping.py tests/test_sync_mapping.py
git commit -m "feat: .mochi.json mapping read/write + content hashing"
```

---

### Task 14: `sync/push.py` — incremental local → Mochi

**Files:**
- Create: `src/mochi_deckgen_mcp/sync/push.py`
- Create: `tests/test_sync_push.py`

- [ ] **Step 1: Write failing tests**

`tests/test_sync_push.py`:

```python
import datetime as _dt
from pathlib import Path

from mochi_deckgen_mcp.local.deck_ops import create_deck, write_card
from mochi_deckgen_mcp.sync.mapping import Mapping, save_mapping
from mochi_deckgen_mcp.sync.push import push_deck


class FakeMochi:
    def __init__(self):
        self.created_decks: list = []
        self.created_cards: list = []
        self.updated_cards: list = []
        self.next_id = 0

    def create_deck(self, name, parent_id=None):
        self.next_id += 1
        d = {"id": f"d{self.next_id}", "name": name}
        self.created_decks.append(d)
        return d

    def create_card(self, deck_id, content, template_id=None, fields=None):
        self.next_id += 1
        c = {"id": f"c{self.next_id}", "deck-id": deck_id, "content": content}
        self.created_cards.append(c)
        return c

    def update_card(self, card_id, **fields):
        self.updated_cards.append({"id": card_id, **fields})
        return {"id": card_id, **fields}


def test_first_push_creates_everything(tmp_path):
    create_deck(tmp_path, "T")
    write_card(tmp_path, "T", 1, "Q1", "A1")
    write_card(tmp_path, "T", 2, "Q2", "A2")

    fm = FakeMochi()
    result = push_deck(tmp_path, "T", fm)
    assert len(fm.created_decks) == 1
    assert len(fm.created_cards) == 2
    assert result["created"] == 2
    assert (tmp_path / "raw" / "T" / ".mochi.json").exists()


def test_second_push_skips_unchanged(tmp_path):
    create_deck(tmp_path, "T")
    write_card(tmp_path, "T", 1, "Q1", "A1")
    fm = FakeMochi()
    push_deck(tmp_path, "T", fm)

    fm2 = FakeMochi()
    result = push_deck(tmp_path, "T", fm2)
    assert result["created"] == 0
    assert result["updated"] == 0


def test_second_push_updates_changed(tmp_path):
    create_deck(tmp_path, "T")
    write_card(tmp_path, "T", 1, "Q1", "A1")
    fm = FakeMochi()
    push_deck(tmp_path, "T", fm)

    write_card(tmp_path, "T", 1, "Q1", "A1-NEW")
    fm2 = FakeMochi()
    result = push_deck(tmp_path, "T", fm2)
    assert result["updated"] == 1
    assert len(fm2.updated_cards) == 1
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `sync/push.py`**

`src/mochi_deckgen_mcp/sync/push.py`:

```python
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from mochi_deckgen_mcp.local.deck_fs import read_deck
from mochi_deckgen_mcp.sync.mapping import Mapping, hash_text, load_mapping, save_mapping


def _card_content(front_md: str, back_md: str, tags: list[str]) -> str:
    body = f"{front_md}\n\n---\n\n{back_md}"
    if tags:
        body += "\n\nTags: " + " ".join(f"#{t}" for t in tags)
    return body


def push_deck(decks_root: Path, deck_name: str, mochi_client, parent_id: str | None = None) -> dict:
    folder = Path(decks_root) / "raw" / deck_name
    deck = read_deck(folder)
    mapping = load_mapping(folder)
    created = 0
    updated = 0

    if mapping is None:
        result = mochi_client.create_deck(name=deck.name, parent_id=parent_id)
        mapping = Mapping(deck_id=result["id"], deck_name_on_mochi=deck.name, parent_id=parent_id)

    for card in deck.cards:
        name = card.source_path.name if card.source_path else ""
        content = _card_content(card.front_md, card.back_md, card.tags)
        digest = hash_text(content)
        prev = mapping.cards.get(name)
        if prev is None:
            r = mochi_client.create_card(deck_id=mapping.deck_id, content=content)
            mapping.cards[name] = {"id": r["id"], "content_hash": digest}
            created += 1
        elif prev["content_hash"] != digest:
            mochi_client.update_card(prev["id"], content=content)
            mapping.cards[name] = {"id": prev["id"], "content_hash": digest}
            updated += 1

    mapping.last_push_at = _dt.datetime.now(_dt.UTC).isoformat().replace("+00:00", "Z")
    save_mapping(folder, mapping)
    return {"deck_id": mapping.deck_id, "created": created, "updated": updated}
```

- [ ] **Step 4: Run tests**

Expected: 3 pass.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/sync/push.py tests/test_sync_push.py
git commit -m "feat: sync push with incremental content-hash diffing"
```

---

### Task 15: `sync/pull.py` — Mochi → local mirror

**Files:**
- Create: `src/mochi_deckgen_mcp/sync/pull.py`
- Create: `tests/test_sync_pull.py`

- [ ] **Step 1: Write failing tests**

`tests/test_sync_pull.py`:

```python
from pathlib import Path

from mochi_deckgen_mcp.sync.pull import pull_deck


class FakeMochi:
    def get_deck(self, deck_id):
        return {"id": deck_id, "name": "Flags"}

    def list_cards(self, deck_id=None, bookmark=None):
        return {"docs": [
            {"id": "c1", "content": "What flag?\n\n---\n\nJapan\n\n![](@media/jp.png)"},
            {"id": "c2", "content": "Capital of France?\n\n---\n\nParis"},
        ], "bookmark": None}


def test_pull_writes_cards_and_mapping(tmp_path):
    out = pull_deck(tmp_path, "d1", FakeMochi())
    folder = tmp_path / "raw" / "Flags"
    assert (folder / "card-001.md").exists()
    assert (folder / "card-002.md").exists()
    assert (folder / ".mochi.json").exists()


def test_pull_rewrites_media_refs_and_warns(tmp_path):
    pull_deck(tmp_path, "d1", FakeMochi())
    folder = tmp_path / "raw" / "Flags"
    first = (folder / "card-001.md").read_text()
    assert "images/jp.png" in first
    assert "@media/" not in first
    warn = (folder / "attachments-not-downloaded.txt").read_text()
    assert "jp.png" in warn
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `sync/pull.py`**

`src/mochi_deckgen_mcp/sync/pull.py`:

```python
from __future__ import annotations

import re
from pathlib import Path

from mochi_deckgen_mcp.sync.mapping import Mapping, hash_text, save_mapping

MEDIA_RE = re.compile(r"@media/([^)\s]+)")


def pull_deck(decks_root: Path, deck_id: str, mochi_client) -> dict:
    deck_meta = mochi_client.get_deck(deck_id)
    folder = Path(decks_root) / "raw" / deck_meta["name"]
    folder.mkdir(parents=True, exist_ok=True)

    missing: set[str] = set()
    mapping = Mapping(deck_id=deck_id, deck_name_on_mochi=deck_meta["name"])

    index = 1
    bookmark = None
    while True:
        page = mochi_client.list_cards(deck_id=deck_id, bookmark=bookmark)
        for card in page["docs"]:
            content = card["content"]
            for m in MEDIA_RE.finditer(content):
                missing.add(m.group(1))
            content = MEDIA_RE.sub(r"images/\1", content)
            name = f"card-{index:03d}.md"
            (folder / name).write_text(content + "\n", encoding="utf-8")
            mapping.cards[name] = {"id": card["id"], "content_hash": hash_text(content)}
            index += 1
        bookmark = page.get("bookmark")
        if not bookmark:
            break

    save_mapping(folder, mapping)
    if missing:
        (folder / "attachments-not-downloaded.txt").write_text(
            "Mochi API does not expose attachment downloads. These files are referenced but not present locally:\n"
            + "\n".join(sorted(missing))
            + "\n",
            encoding="utf-8",
        )
    return {"deck_name": deck_meta["name"], "cards_pulled": index - 1, "missing_images": sorted(missing)}
```

- [ ] **Step 4: Run tests**

Expected: 2 pass.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/sync/pull.py tests/test_sync_pull.py
git commit -m "feat: sync pull with @media→images rewrite + missing-attachments warning"
```

---

### Task 16: `sync/diff.py` (status) and `tools/sync_tools.py`

**Files:**
- Create: `src/mochi_deckgen_mcp/sync/diff.py`
- Create: `src/mochi_deckgen_mcp/tools/sync_tools.py`
- Create: `tests/test_sync_diff.py`
- Create: `tests/test_sync_tools.py`

- [ ] **Step 1: Tests for diff**

`tests/test_sync_diff.py`:

```python
from pathlib import Path

from mochi_deckgen_mcp.local.deck_ops import create_deck, write_card
from mochi_deckgen_mcp.sync.diff import sync_status
from mochi_deckgen_mcp.sync.mapping import Mapping, hash_text, save_mapping


class FakeMochi:
    def __init__(self, cards):
        self._cards = cards
    def list_cards(self, deck_id=None, bookmark=None):
        return {"docs": self._cards, "bookmark": None}


def test_status_reports_categories(tmp_path):
    create_deck(tmp_path, "T")
    write_card(tmp_path, "T", 1, "Q1", "A1")
    write_card(tmp_path, "T", 2, "Q2-NEW", "A2")

    mapping = Mapping(deck_id="d1", deck_name_on_mochi="T")
    mapping.cards["card-001.md"] = {"id": "c1", "content_hash": hash_text("Q1\n\n---\n\nA1")}
    mapping.cards["card-002.md"] = {"id": "c2", "content_hash": hash_text("OLD")}
    save_mapping(tmp_path / "raw" / "T", mapping)

    fm = FakeMochi([{"id": "c1", "content": "Q1\n\n---\n\nA1"}, {"id": "c2", "content": "Q2-NEW\n\n---\n\nA2"}, {"id": "c3", "content": "extra\n\n---\n\nx"}])
    status = sync_status(tmp_path, "T", fm)
    assert "card-002.md" in [s["name"] for s in status if s["status"] == "changed-locally"]
    assert any(s["status"] == "new-remotely" for s in status)
```

- [ ] **Step 2: Implement `sync/diff.py`**

`src/mochi_deckgen_mcp/sync/diff.py`:

```python
from __future__ import annotations

from pathlib import Path

from mochi_deckgen_mcp.local.deck_fs import read_deck
from mochi_deckgen_mcp.sync.mapping import hash_text, load_mapping
from mochi_deckgen_mcp.sync.push import _card_content


def sync_status(decks_root: Path, deck_name: str, mochi_client) -> list[dict]:
    folder = Path(decks_root) / "raw" / deck_name
    deck = read_deck(folder)
    mapping = load_mapping(folder)
    rows: list[dict] = []

    local_by_name: dict[str, str] = {}
    for c in deck.cards:
        name = c.source_path.name if c.source_path else ""
        local_by_name[name] = hash_text(_card_content(c.front_md, c.back_md, c.tags))

    remote_ids: set[str] = set()
    if mapping:
        page = mochi_client.list_cards(deck_id=mapping.deck_id)
        for card in page["docs"]:
            remote_ids.add(card["id"])

    if mapping is None:
        for name in local_by_name:
            rows.append({"name": name, "status": "new-locally"})
        return rows

    for name, h in local_by_name.items():
        prev = mapping.cards.get(name)
        if prev is None:
            rows.append({"name": name, "status": "new-locally"})
        elif prev["content_hash"] != h:
            rows.append({"name": name, "status": "changed-locally"})
        else:
            rows.append({"name": name, "status": "in-sync"})

    mapped_ids = {v["id"] for v in mapping.cards.values()}
    for rid in remote_ids - mapped_ids:
        rows.append({"name": rid, "status": "new-remotely"})
    return rows
```

- [ ] **Step 3: Run diff tests**

Run: `pytest tests/test_sync_diff.py -v`
Expected: pass.

- [ ] **Step 4: Tests for sync tools**

`tests/test_sync_tools.py`:

```python
from mochi_deckgen_mcp.tools import sync_tools


def test_collect_has_expected_tools():
    names = {t["name"] for t in sync_tools.collect()}
    assert names >= {"sync_push_deck", "sync_pull_deck", "sync_status", "sync_link"}


def test_push_without_auth(monkeypatch):
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    tools = {t["name"]: t["fn"] for t in sync_tools.collect()}
    out = tools["sync_push_deck"](deck="X")
    assert out.get("isError") is True
```

- [ ] **Step 5: Implement `tools/sync_tools.py`**

`src/mochi_deckgen_mcp/tools/sync_tools.py`:

```python
from __future__ import annotations

from typing import Any, Callable

from mochi_deckgen_mcp.config import decks_root, mochi_api_key
from mochi_deckgen_mcp.mochi.client import MochiClient
from mochi_deckgen_mcp.sync.diff import sync_status
from mochi_deckgen_mcp.sync.mapping import Mapping, save_mapping
from mochi_deckgen_mcp.sync.pull import pull_deck
from mochi_deckgen_mcp.sync.push import push_deck

_AUTH_HELP = (
    "MOCHI_API_KEY missing. Get a key at https://app.mochi.cards/ → click your avatar → "
    "Account Settings → API Keys, then set MOCHI_API_KEY in your MCP client config."
)


def _err(msg: str) -> dict:
    return {"isError": True, "content": [{"type": "text", "text": msg}]}


def _t(name: str, fn: Callable[..., Any], description: str) -> dict:
    return {"name": name, "fn": fn, "description": description}


def collect() -> list[dict]:
    def _c():
        k = mochi_api_key()
        return MochiClient(api_key=k) if k else None

    def sync_push_deck(deck: str, parent_id: str | None = None) -> Any:
        c = _c()
        if c is None:
            return _err(_AUTH_HELP)
        return push_deck(decks_root(), deck, c, parent_id=parent_id)

    def sync_pull_deck(deck_id: str) -> Any:
        c = _c()
        if c is None:
            return _err(_AUTH_HELP)
        return pull_deck(decks_root(), deck_id, c)

    def sync_status_tool(deck: str) -> Any:
        c = _c()
        if c is None:
            return _err(_AUTH_HELP)
        return sync_status(decks_root(), deck, c)

    def sync_link(deck: str, deck_id: str, deck_name_on_mochi: str | None = None) -> dict:
        folder = decks_root() / "raw" / deck
        m = Mapping(deck_id=deck_id, deck_name_on_mochi=deck_name_on_mochi or deck)
        save_mapping(folder, m)
        return {"linked": str(folder), "deck_id": deck_id}

    return [
        _t("sync_push_deck", sync_push_deck, "Push local deck to Mochi (incremental)."),
        _t("sync_pull_deck", sync_pull_deck, "Pull a Mochi deck into local markdown."),
        _t("sync_status", sync_status_tool, "Compare local vs Mochi for a deck."),
        _t("sync_link", sync_link, "Associate a local folder with a Mochi deck id."),
    ]
```

- [ ] **Step 6: Run all tests**

Run: `pytest tests/test_sync_tools.py tests/test_sync_diff.py -v`
Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/mochi_deckgen_mcp/sync/diff.py src/mochi_deckgen_mcp/tools/sync_tools.py tests/test_sync_diff.py tests/test_sync_tools.py
git commit -m "feat: sync_status diff and sync_tools wrappers"
```

---

## Phase E — Prompts

### Task 17: Prompt-compression line-cap test (gate-first)

**Files:**
- Create: `tests/test_prompt_compression.py`

- [ ] **Step 1: Write the test**

`tests/test_prompt_compression.py`:

```python
from pathlib import Path

ROOT = Path(__file__).parent.parent / "src" / "mochi_deckgen_mcp" / "prompts"
AGENTS = ROOT / "agents"
WORKFLOWS = ROOT / "workflows"

AGENT_MAX = 15
WORKFLOW_MAX = 30


def _non_blank_lines(path: Path) -> int:
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def test_agent_prompts_under_cap():
    files = list(AGENTS.glob("*.md"))
    assert files, "No agent prompts found"
    for f in files:
        n = _non_blank_lines(f)
        assert n <= AGENT_MAX, f"{f.name}: {n} non-blank lines > {AGENT_MAX}"


def test_workflow_prompts_under_cap():
    files = list(WORKFLOWS.glob("*.md"))
    assert files, "No workflow prompts found"
    for f in files:
        n = _non_blank_lines(f)
        assert n <= WORKFLOW_MAX, f"{f.name}: {n} non-blank lines > {WORKFLOW_MAX}"


def test_agent_prompts_start_with_role_line():
    for f in AGENTS.glob("*.md"):
        first = next((l for l in f.read_text().splitlines() if l.strip()), "")
        assert first.startswith("Role:"), f"{f.name} must start with `Role:`"
```

- [ ] **Step 2: Run; expect failure (no prompts yet)**

Run: `pytest tests/test_prompt_compression.py -v`
Expected: `assert files` fails — no agent prompts found.

- [ ] **Step 3: Commit (the test gates Task 18 + 20)**

```bash
git add tests/test_prompt_compression.py
git commit -m "test: prompt-compression line-cap audit (gates §4.1)"
```

---

### Task 18: Layer-2 subagent prompts (all 8)

**Files:**
- Create: `src/mochi_deckgen_mcp/prompts/agents/deck_clarifier.md`
- Create: `src/mochi_deckgen_mcp/prompts/agents/deck_planner.md`
- Create: `src/mochi_deckgen_mcp/prompts/agents/card_compressor.md`
- Create: `src/mochi_deckgen_mcp/prompts/agents/web_card_generator.md`
- Create: `src/mochi_deckgen_mcp/prompts/agents/image_card_creator.md`
- Create: `src/mochi_deckgen_mcp/prompts/agents/image_searcher.md`
- Create: `src/mochi_deckgen_mcp/prompts/agents/card_verifier.md`
- Create: `src/mochi_deckgen_mcp/prompts/agents/card_modifier.md`

- [ ] **Step 1: Write `deck_clarifier.md`**

```markdown
Role: DeckClarifier.

Input: deck description, target size, optional parent deck on Mochi.

Produce 2–4 follow-up questions that resolve ambiguity. Skip anything already implied. Prefer multiple-choice for type/scope questions.

Output JSON: {"questions": [{"id": "snake_case", "question": string, "type": "free" | "choice", "options"?: [string]}]}.
```

- [ ] **Step 2: Write `deck_planner.md`**

```markdown
Role: DeckPlanner.

Input: deck description, target size N, clarifier answers, optional existing-card one-line summaries.

Produce exactly N outline lines. Each line is one atomic fact: prompt → answer hint. Multi-cause requests expand to one line per cause. Avoid duplicates of any existing-card summary.

Output text, one line per card: "NNN. <prompt> → <answer hint>".
```

- [ ] **Step 3: Write `card_compressor.md`**

```markdown
Role: CardCompressor.

Input: one flashcard (front, back, optional tags).

Produce one line summarizing the fact tested. No more than 12 words. Used downstream for dedup and planner context.

Output: a single line of plain text.
```

- [ ] **Step 4: Write `web_card_generator.md`**

```markdown
Role: WebCardGenerator.

Input: one outline line (prompt → answer hint), deck topic, optional prior reviewer critique.

Use web_search if the fact isn't obvious. Produce one atomic card with `front\n\n---\n\nback`. If you cannot phrase it atomically, output the single line `CANNOT_ATOMIZE: <reason>` instead.

Output: markdown card body, or the CANNOT_ATOMIZE failure marker.
```

- [ ] **Step 5: Write `image_card_creator.md`**

```markdown
Role: ImageCardCreator.

Input: concept, side ("front" | "back"), optional image URL or candidate set from ImageSearcher.

Choose one image (prefer Wikipedia source if available). Output a card with the image on the chosen side and an atomic fact on the other. If the concept can't be made atomic with an image, output `CANNOT_ATOMIZE: <reason>`.

Output: markdown card body, or the failure marker.
```

- [ ] **Step 6: Write `image_searcher.md`**

```markdown
Role: ImageSearcher.

Input: concept, optional preferred source.

Call local_fetch_wikipedia_image first; if no hit, web_search for 3–5 candidates. Return URL, thumbnail, brief description, source, license per candidate.

Output JSON: [{"url": string, "thumbnail": string, "description": string, "source": string, "license": string}].
```

- [ ] **Step 7: Write `card_verifier.md`**

```markdown
Role: CardVerifier.

Input: one flashcard (front, back, optional image content), deck topic.

Check in order:
1. Atomic — one fact only. Fail → hard.
2. Binary — back is the unique correct response to front.
3. Format — well-formed sides, no empty side, no stray separator.
4. Factual — verify claims; web_search non-obvious facts.
5. Pedagogical — clear cue on front, concise back.

Output JSON: {"verdict": "pass" | "fail", "severity": "hard" | "soft", "issues": [string]}.
```

- [ ] **Step 8: Write `card_modifier.md`**

```markdown
Role: CardModifier.

Input: one flashcard, a transformation description.

Apply the transformation. Preserve atomicity — if the transformation would combine or split atoms, refuse with `REFUSED: <reason>`. Keep markdown separator and tag line intact.

Output: modified markdown card body, or the REFUSED marker.
```

- [ ] **Step 9: Run line-cap test**

Run: `pytest tests/test_prompt_compression.py -v`
Expected: agent test passes; workflow test still fails (no workflow files yet).

- [ ] **Step 10: Commit**

```bash
git add src/mochi_deckgen_mcp/prompts/agents
git commit -m "feat: Layer-2 subagent prompts (8 files, each ≤15 lines)"
```

---

### Task 19: `.claude/agents/` wrapper files

**Files:**
- Create: `.claude/agents/deck-clarifier.md`
- Create: `.claude/agents/deck-planner.md`
- Create: `.claude/agents/card-compressor.md`
- Create: `.claude/agents/web-card-generator.md`
- Create: `.claude/agents/image-card-creator.md`
- Create: `.claude/agents/image-searcher.md`
- Create: `.claude/agents/card-verifier.md`
- Create: `.claude/agents/card-modifier.md`

- [ ] **Step 1: Write the 8 wrappers**

Each file follows the same pattern. Example for `.claude/agents/deck-clarifier.md`:

```markdown
---
name: deck-clarifier
description: Generate 2-4 follow-up questions to clarify a deck request. Use during generate-deck and extend-deck workflows.
tools: []
---

Role: DeckClarifier.

Input: deck description, target size, optional parent deck on Mochi.

Produce 2–4 follow-up questions that resolve ambiguity. Skip anything already implied. Prefer multiple-choice for type/scope questions.

Output JSON: {"questions": [{"id": "snake_case", "question": string, "type": "free" | "choice", "options"?: [string]}]}.
```

Repeat for the other 7. Use the same body as the corresponding file in `src/mochi_deckgen_mcp/prompts/agents/` and the matching frontmatter:

| File | name | tools |
|---|---|---|
| deck-planner.md | deck-planner | [] |
| card-compressor.md | card-compressor | [] |
| web-card-generator.md | web-card-generator | [WebSearch] |
| image-card-creator.md | image-card-creator | [] |
| image-searcher.md | image-searcher | [WebSearch] |
| card-verifier.md | card-verifier | [WebSearch] |
| card-modifier.md | card-modifier | [] |

- [ ] **Step 2: Commit**

```bash
git add .claude/agents
git commit -m "feat: .claude/agents wrappers for parallel dispatch in Claude Code"
```

---

### Task 20: Layer-3 workflow prompts (all 10)

**Files:**
- Create: `src/mochi_deckgen_mcp/prompts/workflows/quickstart.md`
- Create: `src/mochi_deckgen_mcp/prompts/workflows/generate_deck.md`
- Create: `src/mochi_deckgen_mcp/prompts/workflows/extend_deck.md`
- Create: `src/mochi_deckgen_mcp/prompts/workflows/modify_deck.md`
- Create: `src/mochi_deckgen_mcp/prompts/workflows/review_deck.md`
- Create: `src/mochi_deckgen_mcp/prompts/workflows/merge_decks.md`
- Create: `src/mochi_deckgen_mcp/prompts/workflows/mirror_deck.md`
- Create: `src/mochi_deckgen_mcp/prompts/workflows/delete_deck.md`
- Create: `src/mochi_deckgen_mcp/prompts/workflows/browse_decks.md`
- Create: `src/mochi_deckgen_mcp/prompts/workflows/make_cards_from_image.md`

- [ ] **Step 1: `quickstart.md`**

```markdown
Role: Run the quickstart workflow.

1. Call mochi_list_decks. If it returns isError (auth missing), print the error text verbatim and stop.
2. Show existing Mochi decks with card counts.
3. Ask the user: create new deck / extend existing / modify existing / mirror for local editing / make cards from image.
4. Hand off to the chosen workflow.
```

- [ ] **Step 2: `generate_deck.md`**

```markdown
Role: Run the generate-deck workflow.

1. Ask deck description.
2. Ask card count (default 50).
3. Call mochi_list_decks; show; ask parent deck (optional).
4. Call mochi_list_templates; ask template (or none).
5. Dispatch DeckClarifier → ask the user the returned questions.
6. Dispatch DeckPlanner → outline. Show; accept approve/edit/regenerate.
7. Parallel WebCardGenerator per outline line → local_write_card. Surface any CANNOT_ATOMIZE.
8. local_check_malformed across all cards; queue malformed for regen.
9. Parallel CardVerifier on structurally-valid cards (pass image content for image cards).
10. Each fail: regen with the issue text as critique; re-verify. Cap at DECKGEN_DEFAULT_REGEN; atomicity fails bypass the cap.
11. Summary: pass / regenerated / flagged-final. For each flagged-final: [edit/accept/drop].
12. Ask: push to Mochi now? On yes → sync_push_deck. Report URL + counts.
```

- [ ] **Step 3: `extend_deck.md`**

```markdown
Role: Run the extend-deck workflow.

1. Ask which deck (call local_list_decks + mochi_list_decks for picker).
2. Parallel CardCompressor over existing cards → dedup summaries.
3. Ask what to add (free text, count).
4. Dispatch DeckPlanner with existing-card summaries in context → outline avoiding duplicates.
5. Approve outline.
6. Parallel WebCardGenerator → local_write_card with new indices (max existing + 1, …).
7. local_check_malformed; queue malformed for regen.
8. Parallel CardVerifier; regen failures up to DECKGEN_DEFAULT_REGEN; atomicity bypasses cap.
9. Summary table. Per-card [edit/accept/drop] on flagged-final.
10. sync_push_deck (incremental). Report counts.
```

- [ ] **Step 4: `modify_deck.md`**

```markdown
Role: Run the modify-deck workflow. Presets: swap-sides, to-cloze, make-harder, add-tags, freeform.

1. Ask which deck and which transformation (preset or freeform description).
2. Ask scope: all / by tag / by content match. local_list_cards to confirm.
3. Pick 3 representative cards in scope.
4. Parallel CardModifier on the 3 samples → show before/after diff.
5. User: approve / adjust wording / abort. For global presets (e.g. swap-sides), require a second confirmation.
6. Parallel CardModifier on full scope. Skip and warn on REFUSED outputs.
7. Parallel CardVerifier; revert any card whose modified version fails atomicity.
8. Summary of changed / reverted / flagged.
9. sync_push_deck (incremental).
```

- [ ] **Step 5: `review_deck.md`**

```markdown
Role: Run the review-deck workflow. Modes: auto, manual.

1. Ask which deck and mode.
2. local_check_malformed; list structural failures.
3. auto: parallel CardVerifier; group by severity. For each non-pass: show issue, ask [edit/regen/accept/skip].
4. manual: iterate cards; for each show front+back; ask [keep/edit/regenerate/delete/skip].
5. Apply: CardModifier for "edit", WebCardGenerator for "regen", local_delete_card for "delete".
6. Re-verify the modified subset.
7. sync_push_deck (incremental).
```

- [ ] **Step 6: `merge_decks.md`**

```markdown
Role: Run the merge-decks workflow.

1. Ask deck A, deck B, target name, drop duplicates?, parent on Mochi?
2. Parallel CardCompressor on all cards in both decks.
3. Compare summaries; flag near-duplicates. For each conflict: ask user which copy to keep or merge.
4. local_create_deck target; local_write_card for the merged set.
5. sync_push_deck.
6. Ask: trash the originals? On yes → mochi_trash_deck for each, local_delete_deck for each.
```

- [ ] **Step 7: `mirror_deck.md`**

```markdown
Role: Run the mirror-deck workflow.

1. Disclose: "Mochi's API does not expose attachment downloads. This mirror preserves image references but not the binaries. Continue?"
2. Call mochi_list_decks → numbered list. User picks by index or name.
3. sync_pull_deck on the chosen deck_id.
4. Report cards pulled + any missing images. Point to attachments-not-downloaded.txt.
```

- [ ] **Step 8: `delete_deck.md`**

```markdown
Role: Run the delete-deck workflow.

1. Ask which deck.
2. Show stats: card count, last push, local/mochi/both.
3. Ask: trash (default) or hard-delete? Hard requires typing exactly "DELETE".
4. trash: mochi_trash_deck + local_delete_deck.
5. hard: mochi_delete_deck + local_delete_deck (still soft-moves locally; remind user to purge .trash/ manually).
6. Report.
```

- [ ] **Step 9: `browse_decks.md`**

```markdown
Role: Run the browse-decks workflow.

1. Parallel call: mochi_list_decks, local_list_decks.
2. Merge by deck id from .mochi.json mappings.
3. Show table: name | source (local/mochi/both) | card count | last push | parent.
4. Optional: user supplies a free-text query. Grep local files; paginate mochi_list_cards substring-matched. Show results with card ids and paths.
```

- [ ] **Step 10: `make_cards_from_image.md`**

```markdown
Role: Run the make-cards-from-image workflow. Requires multimodal host LLM.

1. Ask target deck (existing or new).
2. Accept the image (path, base64, or pasted). Call local_import_image.
3. Interpret the image (OCR/diagram-read). Extract atomic facts.
4. Dispatch DeckPlanner with extracted facts → outline.
5. Approve outline.
6. Parallel WebCardGenerator (and ImageCardCreator if sub-regions belong on cards) → local_write_card.
7. local_check_malformed; parallel CardVerifier; regen failures.
8. Summary + per-card actions for flagged-final.
9. sync_push_deck (incremental).
```

- [ ] **Step 11: Run line-cap test**

Run: `pytest tests/test_prompt_compression.py -v`
Expected: all 3 assertions pass.

- [ ] **Step 12: Commit**

```bash
git add src/mochi_deckgen_mcp/prompts/workflows
git commit -m "feat: Layer-3 workflow prompts (10 files, each ≤30 lines)"
```

---

## Phase F — Server

### Task 21: Registry — collect tools and prompts

**Files:**
- Create: `src/mochi_deckgen_mcp/registry.py`
- Create: `tests/test_registry.py`

- [ ] **Step 1: Write failing tests**

`tests/test_registry.py`:

```python
from mochi_deckgen_mcp.registry import all_tools, all_prompts, all_resources


def test_all_tools_combine_local_mochi_sync():
    names = {t["name"] for t in all_tools()}
    assert any(n.startswith("local_") for n in names)
    assert any(n.startswith("mochi_") for n in names)
    assert any(n.startswith("sync_") for n in names)


def test_all_prompts_include_subagents_and_workflows():
    names = {p["name"] for p in all_prompts()}
    assert "card-verifier" in names
    assert "generate-deck" in names
    assert "quickstart" in names


def test_all_resources_include_subagent_files():
    uris = {r["uri"] for r in all_resources()}
    assert any("card-verifier" in u for u in uris)
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `registry.py`**

`src/mochi_deckgen_mcp/registry.py`:

```python
from __future__ import annotations

from pathlib import Path

from mochi_deckgen_mcp.tools import local_tools, mochi_tools, sync_tools

PROMPTS_DIR = Path(__file__).parent / "prompts"
AGENTS_DIR = PROMPTS_DIR / "agents"
WORKFLOWS_DIR = PROMPTS_DIR / "workflows"


def all_tools() -> list[dict]:
    return [*local_tools.collect(), *mochi_tools.collect(), *sync_tools.collect()]


def _slug(p: Path) -> str:
    return p.stem.replace("_", "-")


def all_prompts() -> list[dict]:
    prompts: list[dict] = []
    for p in sorted(AGENTS_DIR.glob("*.md")):
        prompts.append({"name": _slug(p), "path": p, "kind": "agent",
                        "description": f"Subagent: {_slug(p)}"})
    for p in sorted(WORKFLOWS_DIR.glob("*.md")):
        prompts.append({"name": _slug(p), "path": p, "kind": "workflow",
                        "description": f"Workflow: {_slug(p)}"})
    return prompts


def all_resources() -> list[dict]:
    resources: list[dict] = []
    for p in sorted(AGENTS_DIR.glob("*.md")):
        resources.append({
            "uri": f"deckgen://prompts/agents/{_slug(p)}",
            "name": _slug(p),
            "mimeType": "text/markdown",
            "path": p,
        })
    return resources
```

- [ ] **Step 4: Run tests**

Expected: 3 pass.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/registry.py tests/test_registry.py
git commit -m "feat: registry combines tools + prompts + resources"
```

---

### Task 22: `server.py` entry point (FastMCP) + `--agents-path` flag

**Files:**
- Create: `src/mochi_deckgen_mcp/server.py`
- Create: `tests/test_server_registration.py`

- [ ] **Step 1: Write failing tests**

`tests/test_server_registration.py`:

```python
import json
import subprocess
import sys
from pathlib import Path


def test_agents_path_flag():
    out = subprocess.check_output([sys.executable, "-m", "mochi_deckgen_mcp.server", "--agents-path"]).decode().strip()
    p = Path(out)
    assert p.exists()
    assert p.is_dir()


def test_server_registers_all_tools_and_prompts():
    from mochi_deckgen_mcp.server import build_server
    server = build_server()
    tool_names = {t.name for t in server._tool_manager.list_tools()}
    assert "local_create_deck" in tool_names
    assert "mochi_list_decks" in tool_names
    assert "sync_push_deck" in tool_names

    prompt_names = {p.name for p in server._prompt_manager.list_prompts()}
    assert "generate-deck" in prompt_names
    assert "card-verifier" in prompt_names
```

- [ ] **Step 2: Run; expect failure**

- [ ] **Step 3: Implement `server.py`**

`src/mochi_deckgen_mcp/server.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from mochi_deckgen_mcp.registry import AGENTS_DIR, all_prompts, all_resources, all_tools


def build_server() -> FastMCP:
    server = FastMCP("deckgen")

    for tool in all_tools():
        server.add_tool(tool["fn"], name=tool["name"], description=tool["description"])

    for prompt in all_prompts():
        content = prompt["path"].read_text(encoding="utf-8")

        def make_handler(text: str):
            def handler() -> str:
                return text
            return handler

        server.add_prompt(make_handler(content), name=prompt["name"], description=prompt["description"])

    for resource in all_resources():
        text = Path(resource["path"]).read_text(encoding="utf-8")

        def make_reader(t: str):
            def reader() -> str:
                return t
            return reader

        server.add_resource(
            make_reader(text),
            uri=resource["uri"],
            name=resource["name"],
            mime_type=resource["mimeType"],
        )

    return server


def main() -> None:
    parser = argparse.ArgumentParser(prog="mochi-deckgen-mcp")
    parser.add_argument("--agents-path", action="store_true",
                        help="Print the path to the bundled .claude/agents/ directory and exit.")
    args = parser.parse_args()

    if args.agents_path:
        repo_agents = Path(__file__).parent.parent.parent / ".claude" / "agents"
        if repo_agents.exists():
            print(repo_agents.resolve())
        else:
            print(AGENTS_DIR.resolve())
        sys.exit(0)

    build_server().run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_server_registration.py -v`
Expected: 2 pass.

Note: if FastMCP's manager attribute names differ in the installed version, adjust the assertions in the test to use the equivalent listing API (`server.list_tools()` etc.). Update both server.py and the test if needed; record the API used as a comment.

- [ ] **Step 5: Commit**

```bash
git add src/mochi_deckgen_mcp/server.py tests/test_server_registration.py
git commit -m "feat: FastMCP server entry + --agents-path flag"
```

---

## Phase G — Quality gate

### Task 23: `scripts/verify.sh` — single command runs all gates

**Files:**
- Create: `scripts/verify.sh`

- [ ] **Step 1: Write the script**

`scripts/verify.sh`:

```bash
#!/usr/bin/env bash
set -e

echo "==> pytest"
pytest -q

echo "==> coverage"
coverage run -m pytest -q
coverage report --fail-under=85 \
    --include='src/mochi_deckgen_mcp/local/*,src/mochi_deckgen_mcp/mochi/*,src/mochi_deckgen_mcp/sync/*,src/mochi_deckgen_mcp/tools/*'

echo "==> ruff check"
ruff check .

echo "==> ruff format --check"
ruff format --check .

echo "==> mypy --strict"
mypy src/mochi_deckgen_mcp

echo "==> prompt compression"
pytest tests/test_prompt_compression.py -q

echo "==> server registration smoke"
pytest tests/test_server_registration.py -q

echo
echo "ALL GREEN"
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x scripts/verify.sh
git add scripts/verify.sh
git commit -m "chore: scripts/verify.sh runs the full quality gate"
```

---

### Task 24: README rewrite

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README**

`README.md`:

````markdown
# mochi-deckgen-mcp

An MCP server for generating, modifying, and syncing [Mochi](https://app.mochi.cards) flashcard decks. Drop it into any MCP-capable client (Claude Code, Claude Desktop, Cursor, Goose, Zed) and you get 10 named workflows for deck management — all driven by the host's LLM, with no server-side API key beyond your Mochi key.

## What you get

- Full Mochi CRUD parity with `itzcull/mochi-mcp`, plus everything that tool lacks.
- Bidirectional local↔Mochi sync with content-hash incremental push.
- 10 workflow prompts: `quickstart`, `generate-deck`, `extend-deck`, `modify-deck`, `review-deck`, `merge-decks`, `mirror-deck`, `delete-deck`, `browse-decks`, `make-cards-from-image`.
- 8 reusable subagent prompts (planner, generator, verifier, modifier, compressor, clarifier, image-card-creator, image-searcher).
- Atomic-card quality gate: every card is simple, atomic, binary. Non-negotiable.
- Image-first design: Wikipedia Commons fetcher, image post-processing (resize/EXIF/dedup/SVG→PNG), user-supplied images, vision-aware verification.
- All prompts are tight: subagent prompts ≤15 lines, workflow prompts ≤30 lines.

## Install

```bash
pip install git+https://github.com/oh54321/mochi-deckgen-mcp.git
# Optional: enable SVG → PNG conversion (Wikipedia flag SVGs etc.)
pip install 'mochi-deckgen-mcp[svg]'
```

You'll need a Mochi API key. Get one at https://app.mochi.cards/ → click your avatar → Account Settings → API Keys.

## Wire up

### Claude Code (recommended)

```bash
claude mcp add deckgen --env MOCHI_API_KEY=mochi_xxx -- mochi-deckgen-mcp
ln -s "$(mochi-deckgen-mcp --agents-path)" ~/.claude/agents/deckgen
```

Line 2 enables parallel subagent dispatch. Skip it and workflows still run, just serially.

### Claude Desktop / Cursor / Goose / Zed

Add to your MCP config:

```json
{
  "mcpServers": {
    "deckgen": {
      "command": "mochi-deckgen-mcp",
      "env": {"MOCHI_API_KEY": "mochi_xxx"}
    }
  }
}
```

## Quickstart

In your client, invoke the `quickstart` prompt. It checks your Mochi auth, lists your existing decks, and routes you to the right workflow.

## Environment

| Var | Required? | Default | Effect |
|---|---|---|---|
| `MOCHI_API_KEY` | for `mochi_*` and `sync_*` tools | – | HTTP Basic auth |
| `DECKGEN_DECKS_ROOT` | optional | `~/.local/share/mochi-deckgen-mcp/decks/` | Override to `./decks` to hand-edit cards |
| `DECKGEN_DEFAULT_REGEN` | optional | `1` | Max regen attempts on failed verification |
| `DECKGEN_DEFAULT_CONCURRENCY` | optional | `10` | Hint to workflows for parallel batch size |

## Performance

| Client | 50-card generate | 50-card verify |
|---|---|---|
| Claude Code (parallel `Agent` dispatch) | ~30–60s | ~30–60s |
| Claude Desktop / Cursor / Goose / Zed (serial) | ~5–10min | ~5–10min |

For decks > 20 cards, Claude Code is strongly preferred.

## Card design principles

Generated cards satisfy:

- **Simple** — one concept per card.
- **Atomic** — tests one fact, association, or relationship. Cannot be subdivided.
- **Binary** — back is the unique correct response to the front. No "approximately."

The front does *not* have to be a question. Valid fronts include images-to-identify, terms-to-define, cloze deletions, translation prompts, expressions to simplify, diagrams. What matters is the unique success condition.

Reference: Andy Matuschak, *How to write good prompts*. SuperMemo, *20 rules of formulating knowledge*.

## Development

```bash
pip install -e ".[dev,svg]"
./scripts/verify.sh    # full quality gate (pytest, coverage, ruff, mypy, prompt audit, server smoke)
```

### Manual integration test (before any release)

1. Set `MOCHI_API_KEY` to a key on a sandbox Mochi account.
2. Run each workflow once:
   - `quickstart` → confirm auth check passes
   - `generate-deck` ("Flags of Africa", 5 cards)
   - `extend-deck` (add 2 more)
   - `modify-deck` (swap-sides preset)
   - `review-deck` (auto mode, then manual)
   - `merge-decks`
   - `mirror-deck` on an existing Mochi deck with images
   - `make-cards-from-image` (paste a textbook screenshot)
   - `browse-decks` (with and without query)
   - `delete-deck` (trash mode)
3. Confirm cards appear in Mochi for each push step.

## License

MIT.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for MCP server distribution"
```

---

## Phase H — Delete old code

### Task 25: Delete the legacy `deckgen` package and old tests

**Files:**
- Delete: `src/deckgen/` (entire directory)
- Delete: `scripts/generate.py`, `scripts/export_only.py`
- Delete: `tests/test_anthropic_client_smoke.py`, `test_cli_args.py`, `test_export_*.py`, `test_fake_client.py`, `test_orchestrator_e2e.py`, `test_pipeline_*.py`, `test_export_only_script.py`
- Delete: `tests/test_parse_card.py`, `tests/test_read_deck.py`, `tests/test_image_fetch.py` (old versions — superseded by new package tests)
- Delete: `tests/fixtures/` (superseded by `tests/fixtures_new/`)

- [ ] **Step 1: Remove the legacy package**

```bash
rm -rf src/deckgen
```

- [ ] **Step 2: Remove the legacy scripts**

```bash
rm -f scripts/generate.py scripts/export_only.py
```

- [ ] **Step 3: Remove the legacy tests**

```bash
rm -f tests/test_anthropic_client_smoke.py
rm -f tests/test_cli_args.py
rm -f tests/test_export_anki.py tests/test_export_csv.py tests/test_export_markdown_zip.py tests/test_export_mochi.py tests/test_export_only_script.py
rm -f tests/test_fake_client.py
rm -f tests/test_orchestrator_e2e.py
rm -f tests/test_pipeline_clarify.py tests/test_pipeline_export.py tests/test_pipeline_generate.py tests/test_pipeline_plan.py tests/test_pipeline_research.py tests/test_pipeline_verify.py
rm -f tests/test_parse_card.py tests/test_read_deck.py tests/test_image_fetch.py
rm -rf tests/fixtures
rm -rf tests/__pycache__ tests/conftest.py
```

- [ ] **Step 4: Rename the new fixtures directory to `tests/fixtures`**

```bash
mv tests/fixtures_new tests/fixtures
```

Update the import path in any test that referenced `fixtures_new`:

```bash
grep -rl "fixtures_new" tests/ | xargs sed -i 's|fixtures_new|fixtures|g'
```

- [ ] **Step 5: Add a clean `conftest.py`**

`tests/conftest.py`:

```python
import os
import pytest


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    # Ensure tests never accidentally hit a real Mochi account or persist outside tmp.
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    monkeypatch.delenv("DECKGEN_DECKS_ROOT", raising=False)
    yield
```

Then unset that autouse for tests that explicitly set MOCHI_API_KEY by inspecting; those tests already set it explicitly, which overrides the delenv.

Actually replace the autouse approach with a per-test opt-in fixture:

```python
import pytest


@pytest.fixture
def isolated_env(monkeypatch):
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    monkeypatch.delenv("DECKGEN_DECKS_ROOT", raising=False)
    yield
```

(The new test files already manipulate env explicitly with `monkeypatch.setenv` / `monkeypatch.delenv`, so an autouse fixture is unnecessary.)

- [ ] **Step 6: Run the full suite**

Run: `pytest -q`
Expected: all tests pass with the legacy code gone.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: delete legacy deckgen package and its tests"
```

---

### Task 26: Final verification — run the quality gate

**Files:**
- None (verification only)

- [ ] **Step 1: Install dev extras (if not already)**

Run: `pip install -e ".[dev,svg]"`

- [ ] **Step 2: Run `./scripts/verify.sh`**

Run: `./scripts/verify.sh`
Expected: prints `ALL GREEN`.

If any step fails: fix the root cause, re-run. Do not bypass. Common likely issues:
- ruff line-length warnings — wrap the offending line.
- mypy strict failures — add missing type annotations.
- coverage < 85% on a kept module — add targeted tests, do not lower the threshold without recording why in the commit message.

- [ ] **Step 3: Smoke test the server manually**

```bash
mochi-deckgen-mcp --agents-path
```

Expected: prints an absolute path that exists and contains `.md` files.

- [ ] **Step 4: Record verification in a final commit**

If everything is green and no code changes were needed, no commit is required for this step. If verify.sh required fixes, commit them with `chore: fix issues caught by verify.sh`.

- [ ] **Step 5: Tag the spec as implemented**

In the spec file `docs/specs/2026-05-10-mcp-refactor-design.md`, change the status line:

```markdown
**Status:** Implemented (verify.sh green on <date>)
```

Commit:

```bash
git add docs/specs/2026-05-10-mcp-refactor-design.md
git commit -m "docs: mark MCP refactor spec as implemented"
```

---

## Self-Review

Spec coverage map (every spec section → task that implements it):

| Spec section | Implementing task(s) |
|---|---|
| §3 architecture (layers) | 2 (scaffold), 9/12/16 (Layer-1 tool collectors), 18/20 (Layer-2/3 prompts), 21/22 (server wires them up) |
| §4.1 prompt compression caps | 17 (test gate), 18 + 20 (prompts written within cap) |
| §4.2 atomic-card principle | 18 (in card_verifier.md / web_card_generator.md / deck_planner.md / card_modifier.md hard rules) |
| §4.3 staging-area mental model | 9 (config.decks_root default = XDG) |
| §5 repo layout | 1–22 across all tasks |
| §5.1 deletions | 25 |
| §5.2 keeps | 3 (deck_fs), 5 (image_fetch extended), 4 (malformed_check) |
| §6.1 local tools | 4–9 |
| §6.2 Mochi tools | 11, 12 |
| §6.3 sync tools | 13–16 |
| §7 subagents | 18, 19 |
| §8 workflows | 20 |
| §9 install/wire-up | 24 (README) |
| §10 error handling | 12 + 16 (MOCHI_API_KEY help text), 5 (image fetch warnings), 8 (file-conflict refusal) |
| §11 testing | 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 21, 22 |
| §13 deps | 1 |
| §14 open questions | left open; the §16 spike is documented in the spec, not in this plan |
| §15 perf table | 24 (README) |
| §16 quality gate | 23, 26 |

No spec section is unaddressed.

Placeholder scan: no `TBD`, `TODO`, `implement later`, or "similar to Task N" markers. Every code step shows the actual code. Every test step shows the actual test.

Type consistency: `Mapping`, `MochiClient`, `decks_root()`, `_t()`, `collect()` are named identically across tasks.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-10-mcp-refactor.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Best for a refactor this size because each task is well-bounded and a clean context per task avoids LLM drift.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints. Slower but everything stays in one transcript.

**Which approach?**
