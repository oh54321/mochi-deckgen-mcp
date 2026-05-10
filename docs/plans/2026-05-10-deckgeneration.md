# DeckGeneration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-contained Python package that turns a topic description into a spaced-repetition deck, exportable to Mochi (`.mochi`), Anki (`.apkg`), markdown zip, and CSV. Two run paths: a script using the Anthropic API, and a Claude Code skill.

**Architecture:** Pipeline stages (clarify → plan → research → generate → verify → export) coordinated by an orchestrator. An `LLMClient` protocol abstracts the LLM. The same prompts and pipeline run in both modes. Decks live on disk as folders of markdown files; exporters convert them to target formats.

**Tech Stack:** Python 3.11+, `anthropic`, `httpx`, `python-dotenv`, `genanki`, `pydantic`, `rich`, `pytest`, `pytest-asyncio`, `ruff`.

**Spec:** `docs/specs/2026-05-10-deckgeneration-design.md`

---

## Conventions used throughout this plan

- Commands assume the project root: `~/Documents/Code/DeckGeneration`.
- TDD where the unit has a deterministic contract (parsers, exporters, dataclasses). For LLM-call modules, write structural tests against a `FakeLLMClient` rather than the live API.
- One commit per task unless noted. Commit messages use Conventional Commits.
- Python uses type hints throughout; tests use pytest.
- Prompts live as `.md` files under `src/deckgen/prompts/`. Keep prompts terse — state the role, the I/O contract, and hard rules. Skip over-specification.

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/deckgen/__init__.py`
- Create: `src/deckgen/config.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `decks/raw/.gitkeep`
- Create: `decks/exported/.gitkeep`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "deckgen"
version = "0.1.0"
description = "Generate Mochi/Anki decks from a topic description"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.40",
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "genanki>=0.13",
    "pydantic>=2.6",
    "rich>=13.7",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "ruff>=0.5"]

[project.scripts]
deckgen = "deckgen.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/deckgen"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 2: Write `.gitignore`**

```
.env
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
dist/
build/
*.egg-info/
decks/raw/*
!decks/raw/.gitkeep
decks/exported/*
!decks/exported/.gitkeep
.venv/
```

- [ ] **Step 3: Write `.env.example`**

```
# Get a key at https://console.anthropic.com
ANTHROPIC_API_KEY=
```

- [ ] **Step 4: Write `src/deckgen/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 5: Write `src/deckgen/config.py`**

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_CONCURRENCY = 10
DEFAULT_REGEN = 1
DEFAULT_SIZE = 50
DEFAULT_FORMATS = ("mochi",)

REPO_ROOT = Path(__file__).resolve().parents[2]
DECKS_RAW = REPO_ROOT / "decks" / "raw"
DECKS_EXPORTED = REPO_ROOT / "decks" / "exported"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


@dataclass
class Config:
    api_key: str | None
    model: str = DEFAULT_MODEL
    concurrency: int = DEFAULT_CONCURRENCY
    regen: int = DEFAULT_REGEN

    @classmethod
    def from_env(cls) -> "Config":
        return cls(api_key=os.environ.get("ANTHROPIC_API_KEY"))
```

- [ ] **Step 6: Write `tests/__init__.py`** (empty file) and `tests/conftest.py`

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
```

- [ ] **Step 7: Create empty placeholder files**

```bash
touch decks/raw/.gitkeep decks/exported/.gitkeep
```

- [ ] **Step 8: Verify install**

Run: `pip install -e ".[dev]"`
Expected: Success, `pytest` runs (0 tests collected is fine).

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml .gitignore .env.example src/ tests/ decks/
git commit -m "chore: project scaffold"
```

---

## Task 2: Card dataclass + parser

**Files:**
- Create: `src/deckgen/io/__init__.py`
- Create: `src/deckgen/io/deck_fs.py`
- Test: `tests/test_parse_card.py`
- Create: `tests/fixtures/sample_deck/card-001.md`
- Create: `tests/fixtures/sample_deck/card-002.md`
- Create: `tests/fixtures/sample_deck/card-003.md`
- Create: `tests/fixtures/sample_deck/images/jp.png` (empty file, just for path testing)

- [ ] **Step 1: Create the fixture cards**

`tests/fixtures/sample_deck/card-001.md`:
```markdown
What country has this flag?

![](images/jp.png)

---

Japan

Adopted 1999.

Tags: #asia #island-nations
```

`tests/fixtures/sample_deck/card-002.md`:
```markdown
What is $\int_0^1 x\, dx$?

---

$\frac{1}{2}$
```

`tests/fixtures/sample_deck/card-003.md`:
```markdown
Front line one
---
in front body literal
---

Back

Tags: #edge-case
```

(The third fixture covers the "first `---` only" rule.)

Run: `touch tests/fixtures/sample_deck/images/jp.png` (after `mkdir -p` for the parent).

- [ ] **Step 2: Write failing tests in `tests/test_parse_card.py`**

```python
from pathlib import Path

import pytest

from deckgen.io.deck_fs import Card, read_card

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


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
    # The literal "---" after "Front line one" stays inside the front.
    assert "in front body literal" in card.front_md
    assert card.back_md.startswith("Back")
    assert card.tags == ["edge-case"]


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_card(FIXTURE / "does-not-exist.md")
```

- [ ] **Step 3: Run tests; verify they fail**

Run: `pytest tests/test_parse_card.py -v`
Expected: ImportError or test failures (module not yet written).

- [ ] **Step 4: Implement `src/deckgen/io/__init__.py`** (empty file).

- [ ] **Step 5: Implement `src/deckgen/io/deck_fs.py`**

```python
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

TAGS_RE = re.compile(r"^Tags:\s*((?:#\S+\s*)+)$", re.MULTILINE)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
SPLIT_RE = re.compile(r"(?m)^---\s*\n\s*\n")  # `---` line followed by a blank line


@dataclass
class Card:
    front_md: str
    back_md: str
    tags: list[str] = field(default_factory=list)
    image_paths: list[Path] = field(default_factory=list)
    source_path: Path | None = None


def read_card(path: Path) -> Card:
    text = Path(path).read_text(encoding="utf-8")
    parts = SPLIT_RE.split(text, maxsplit=1)
    if len(parts) != 2:
        raise ValueError(f"Card {path} missing front/back separator")
    front, back = parts[0].strip("\n"), parts[1].strip("\n")

    tags: list[str] = []
    m = TAGS_RE.search(back)
    if m:
        tags = [t.lstrip("#") for t in m.group(1).split()]
        back = back[: m.start()].rstrip("\n")

    images = [Path(p) for p in IMAGE_RE.findall(front + "\n" + back)]
    return Card(front_md=front, back_md=back, tags=tags, image_paths=images, source_path=Path(path))
```

- [ ] **Step 6: Run tests; verify pass**

Run: `pytest tests/test_parse_card.py -v`
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add src/deckgen/io/ tests/test_parse_card.py tests/fixtures/
git commit -m "feat(io): card parser with front/back/tags/images"
```

---

## Task 3: Deck reader and `deck.json`

**Files:**
- Modify: `src/deckgen/io/deck_fs.py`
- Test: `tests/test_read_deck.py`
- Create: `tests/fixtures/sample_deck/deck.json`

- [ ] **Step 1: Create `tests/fixtures/sample_deck/deck.json`**

```json
{
  "name": "Sample",
  "description": "Three-card fixture for tests",
  "created_at": "2026-05-10T00:00:00Z",
  "generator_version": "0.1.0",
  "source_topic": "test fixture",
  "follow_up_answers": {}
}
```

- [ ] **Step 2: Write failing test `tests/test_read_deck.py`**

```python
from pathlib import Path

from deckgen.io.deck_fs import read_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_read_deck_loads_metadata_and_cards():
    deck = read_deck(FIXTURE)
    assert deck.name == "Sample"
    assert deck.description.startswith("Three-card")
    assert len(deck.cards) == 3
    # Sorted by filename
    assert deck.cards[0].source_path.name == "card-001.md"
    assert deck.cards[2].source_path.name == "card-003.md"


def test_read_deck_skips_broken_files(tmp_path):
    (tmp_path / "deck.json").write_text('{"name":"X","description":"d"}')
    (tmp_path / "card-001.md").write_text("front\n---\nback")
    (tmp_path / "card-002.md.broken").write_text("garbage")
    deck = read_deck(tmp_path)
    assert len(deck.cards) == 1
```

- [ ] **Step 3: Run; verify fails**

Run: `pytest tests/test_read_deck.py -v`
Expected: fail (`read_deck` not defined).

- [ ] **Step 4: Extend `src/deckgen/io/deck_fs.py`**

Append:

```python
import json


@dataclass
class Deck:
    name: str
    description: str
    cards: list[Card]
    metadata: dict
    folder: Path


def read_deck(folder: Path) -> Deck:
    folder = Path(folder)
    meta = json.loads((folder / "deck.json").read_text(encoding="utf-8"))
    cards = [
        read_card(p)
        for p in sorted(folder.glob("card-*.md"))
        if not p.name.endswith(".broken")
    ]
    return Deck(
        name=meta["name"],
        description=meta.get("description", ""),
        cards=cards,
        metadata=meta,
        folder=folder,
    )
```

- [ ] **Step 5: Run; verify pass**

Run: `pytest tests/test_read_deck.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add src/deckgen/io/deck_fs.py tests/test_read_deck.py tests/fixtures/sample_deck/deck.json
git commit -m "feat(io): deck reader with deck.json metadata"
```

---

## Task 4: Image fetcher

**Files:**
- Create: `src/deckgen/io/image_fetch.py`
- Test: `tests/test_image_fetch.py`

- [ ] **Step 1: Write failing test**

```python
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
```

- [ ] **Step 2: Run; verify fails**

Run: `pytest tests/test_image_fetch.py -v`

- [ ] **Step 3: Implement `src/deckgen/io/image_fetch.py`**

```python
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
```

- [ ] **Step 4: Run; verify pass**

Run: `pytest tests/test_image_fetch.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/deckgen/io/image_fetch.py tests/test_image_fetch.py
git commit -m "feat(io): image fetcher with content-type aware extension"
```

---

## Task 5: CSV exporter

**Files:**
- Create: `src/deckgen/exporters/__init__.py`
- Create: `src/deckgen/exporters/csv_export.py`
- Test: `tests/test_export_csv.py`

- [ ] **Step 1: Write failing test**

```python
import csv as _csv
from pathlib import Path

from deckgen.exporters.csv_export import export_csv
from deckgen.io.deck_fs import read_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_export_csv_three_rows(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_csv(deck, tmp_path)
    assert out.name == "Sample.csv"
    rows = list(_csv.reader(out.open(encoding="utf-8")))
    assert rows[0] == ["front", "back", "tags"]
    assert len(rows) == 4
    # row 1 = first card
    assert "Japan" in rows[1][1]
    assert rows[1][2] == "asia,island-nations"
```

- [ ] **Step 2: Run; verify fails**

Run: `pytest tests/test_export_csv.py -v`

- [ ] **Step 3: Implement**

`src/deckgen/exporters/__init__.py` — empty.

`src/deckgen/exporters/csv_export.py`:

```python
from __future__ import annotations

import csv
from pathlib import Path

from deckgen.io.deck_fs import Deck


def export_csv(deck: Deck, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{deck.name}.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["front", "back", "tags"])
        for c in deck.cards:
            w.writerow([c.front_md, c.back_md, ",".join(c.tags)])
    return path
```

- [ ] **Step 4: Run; verify pass**

Run: `pytest tests/test_export_csv.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/deckgen/exporters/ tests/test_export_csv.py
git commit -m "feat(export): CSV exporter"
```

---

## Task 6: Markdown zip exporter

**Files:**
- Create: `src/deckgen/exporters/markdown_zip.py`
- Test: `tests/test_export_markdown_zip.py`

- [ ] **Step 1: Write failing test**

```python
import zipfile
from pathlib import Path

from deckgen.exporters.markdown_zip import export_markdown_zip
from deckgen.io.deck_fs import read_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_zip_contains_all_card_files_and_images(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_markdown_zip(deck, tmp_path)
    assert out.name == "Sample.zip"
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
    assert "card-001.md" in names
    assert "card-002.md" in names
    assert "card-003.md" in names
    assert "deck.json" in names
    assert "images/jp.png" in names
```

- [ ] **Step 2: Run; verify fails**

Run: `pytest tests/test_export_markdown_zip.py -v`

- [ ] **Step 3: Implement `src/deckgen/exporters/markdown_zip.py`**

```python
from __future__ import annotations

import zipfile
from pathlib import Path

from deckgen.io.deck_fs import Deck


def export_markdown_zip(deck: Deck, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{deck.name}.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(deck.folder.rglob("*")):
            if p.is_dir() or p.name.endswith(".broken"):
                continue
            z.write(p, arcname=p.relative_to(deck.folder))
    return path
```

- [ ] **Step 4: Run; verify pass**

Run: `pytest tests/test_export_markdown_zip.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/deckgen/exporters/markdown_zip.py tests/test_export_markdown_zip.py
git commit -m "feat(export): markdown zip exporter"
```

---

## Task 7: Anki exporter

**Files:**
- Create: `src/deckgen/exporters/anki.py`
- Test: `tests/test_export_anki.py`

- [ ] **Step 1: Write failing test**

```python
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from deckgen.exporters.anki import export_anki
from deckgen.io.deck_fs import read_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_apkg_contains_three_notes_and_media(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_anki(deck, tmp_path)
    assert out.name == "Sample.apkg"

    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
        assert "collection.anki2" in names
        # media manifest exists; one media file (the image)
        assert "media" in names

        with tempfile.TemporaryDirectory() as d:
            z.extract("collection.anki2", d)
            con = sqlite3.connect(Path(d) / "collection.anki2")
            (n,) = con.execute("SELECT COUNT(*) FROM notes").fetchone()
            assert n == 3
```

- [ ] **Step 2: Run; verify fails**

Run: `pytest tests/test_export_anki.py -v`

- [ ] **Step 3: Implement `src/deckgen/exporters/anki.py`**

```python
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import genanki

from deckgen.io.deck_fs import Deck

MODEL_TEMPLATE = {
    "name": "DeckgenBasic",
    "fields": [{"name": "Front"}, {"name": "Back"}],
    "templates": [
        {
            "name": "Card 1",
            "qfmt": "{{Front}}",
            "afmt": "{{FrontSide}}<hr id='answer'>{{Back}}",
        }
    ],
}

IMAGE_RE = re.compile(r"!\[[^\]]*\]\((images/[^)]+)\)")


def _stable_id(name: str, salt: str) -> int:
    return int(hashlib.sha1(f"{name}|{salt}".encode()).hexdigest()[:8], 16)


def _md_to_anki(text: str) -> str:
    # Anki accepts HTML. Convert relative image refs to <img src="filename">.
    return IMAGE_RE.sub(lambda m: f'<img src="{Path(m.group(1)).name}">', text)


def export_anki(deck: Deck, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model = genanki.Model(
        _stable_id(deck.name, "model"),
        MODEL_TEMPLATE["name"],
        fields=MODEL_TEMPLATE["fields"],
        templates=MODEL_TEMPLATE["templates"],
    )
    adeck = genanki.Deck(_stable_id(deck.name, "deck"), deck.name)

    media: list[str] = []
    for card in deck.cards:
        note = genanki.Note(
            model=model,
            fields=[_md_to_anki(card.front_md), _md_to_anki(card.back_md)],
            tags=card.tags,
        )
        adeck.add_note(note)
        for ip in card.image_paths:
            abs_path = deck.folder / ip
            if abs_path.exists():
                media.append(str(abs_path))

    path = out_dir / f"{deck.name}.apkg"
    genanki.Package(adeck, media_files=media).write_to_file(str(path))
    return path
```

- [ ] **Step 4: Run; verify pass**

Run: `pytest tests/test_export_anki.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/deckgen/exporters/anki.py tests/test_export_anki.py
git commit -m "feat(export): Anki .apkg exporter via genanki"
```

---

## Task 8: Mochi exporter

**Files:**
- Create: `src/deckgen/exporters/mochi.py`
- Test: `tests/test_export_mochi.py`

Mochi `.mochi` files are zips containing `data.edn` and image attachments. We hand-write a small EDN subset.

- [ ] **Step 1: Write failing test**

```python
import zipfile
from pathlib import Path

from deckgen.exporters.mochi import export_mochi
from deckgen.io.deck_fs import read_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_mochi_zip_has_data_edn_and_images(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_mochi(deck, tmp_path)
    assert out.name == "Sample.mochi"
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
        assert "data.edn" in names
        # original image is included as an attachment
        assert any(n.startswith("attachments/") for n in names)
        edn = z.read("data.edn").decode("utf-8")

    assert ":version" in edn
    assert ":decks" in edn
    assert ":cards" in edn
    # All three cards appear (front lines as a quick fingerprint)
    assert "Japan" in edn
    assert "\\\\int_0^1" in edn or "\\int_0^1" in edn
```

- [ ] **Step 2: Run; verify fails**

Run: `pytest tests/test_export_mochi.py -v`

- [ ] **Step 3: Implement `src/deckgen/exporters/mochi.py`**

```python
from __future__ import annotations

import hashlib
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from deckgen.io.deck_fs import Card, Deck

IMAGE_RE = re.compile(r"!\[([^\]]*)\]\((images/[^)]+)\)")


def _short_id(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:8]


def _edn_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


@dataclass
class _Attachment:
    arcname: str          # path inside the zip: "attachments/<id>.png"
    attach_id: str        # the EDN @id used in card content
    abs_source: Path


def _card_content(card: Card, attachments_by_path: dict[str, _Attachment]) -> str:
    def repl(m: re.Match) -> str:
        alt, rel = m.group(1), m.group(2)
        att = attachments_by_path.get(rel)
        if att is None:
            return m.group(0)
        return f"![{alt}](@{att.attach_id})"

    front = IMAGE_RE.sub(repl, card.front_md)
    back = IMAGE_RE.sub(repl, card.back_md)
    return f"{front}\n---\n{back}"


def export_mochi(deck: Deck, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Collect attachments
    attachments: dict[str, _Attachment] = {}
    for c in deck.cards:
        for rel in c.image_paths:
            rel_s = str(rel)
            if rel_s in attachments:
                continue
            src = deck.folder / rel
            if not src.exists():
                continue
            aid = _short_id(deck.name, rel_s)
            attachments[rel_s] = _Attachment(
                arcname=f"attachments/{aid}{src.suffix}",
                attach_id=aid,
                abs_source=src,
            )

    deck_id = _short_id(deck.name, "deck")

    # Build EDN
    lines: list[str] = ["{:version 2"]
    lines.append(f" :decks [{{:id {_edn_str(deck_id)} :name {_edn_str(deck.name)} :cards [")
    for i, c in enumerate(deck.cards):
        cid = _short_id(deck.name, str(i))
        name = c.front_md.splitlines()[0][:80] if c.front_md.splitlines() else f"Card {i+1}"
        content = _card_content(c, attachments)
        tag_vec = " ".join(_edn_str(t) for t in c.tags)
        lines.append(
            f"  {{:id {_edn_str(cid)} :name {_edn_str(name)} "
            f":content {_edn_str(content)} "
            f":deck-id {_edn_str(deck_id)} "
            f":tags [{tag_vec}]}}"
        )
    lines.append(" ]}]}")
    edn = "\n".join(lines)

    path = out_dir / f"{deck.name}.mochi"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("data.edn", edn)
        for att in attachments.values():
            z.write(att.abs_source, arcname=att.arcname)
    return path
```

- [ ] **Step 4: Run; verify pass**

Run: `pytest tests/test_export_mochi.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/deckgen/exporters/mochi.py tests/test_export_mochi.py
git commit -m "feat(export): Mochi .mochi exporter (EDN + zip)"
```

---

## Task 9: LLMClient protocol + Anthropic implementation

**Files:**
- Create: `src/deckgen/llm/__init__.py`
- Create: `src/deckgen/llm/client.py`
- Create: `src/deckgen/llm/anthropic_client.py`
- Test: `tests/test_anthropic_client_smoke.py` (skipped without an API key)

- [ ] **Step 1: Write the protocol — `src/deckgen/llm/__init__.py`** (empty), then `src/deckgen/llm/client.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMRequest:
    system: str
    user: str
    tools: list[str] = field(default_factory=list)  # e.g. ["web_search"]
    max_tokens: int = 2048
    temperature: float = 0.5


@dataclass
class LLMResponse:
    text: str
    raw: object = None


class LLMClient(Protocol):
    async def complete(self, req: LLMRequest) -> LLMResponse: ...
```

- [ ] **Step 2: Implement `src/deckgen/llm/anthropic_client.py`**

```python
from __future__ import annotations

import asyncio
import logging
import random

from anthropic import AsyncAnthropic, APIStatusError, RateLimitError

from deckgen.config import Config
from deckgen.llm.client import LLMRequest, LLMResponse

log = logging.getLogger(__name__)


class AnthropicClient:
    def __init__(self, config: Config):
        if not config.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set; copy .env.example to .env")
        self._client = AsyncAnthropic(api_key=config.api_key)
        self._model = config.model

    async def complete(self, req: LLMRequest) -> LLMResponse:
        tools = []
        if "web_search" in req.tools:
            tools.append({"type": "web_search_20250828", "name": "web_search"})

        for attempt in range(5):
            try:
                resp = await self._client.messages.create(
                    model=self._model,
                    system=req.system,
                    max_tokens=req.max_tokens,
                    temperature=req.temperature,
                    tools=tools or None,
                    messages=[{"role": "user", "content": req.user}],
                )
                text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
                return LLMResponse(text=text, raw=resp)
            except (RateLimitError, APIStatusError) as e:
                if attempt == 4:
                    raise
                delay = (2 ** attempt) + random.uniform(0, 1)
                log.warning("LLM retry %d/5 after %s: %.1fs", attempt + 1, type(e).__name__, delay)
                await asyncio.sleep(delay)
        raise RuntimeError("unreachable")
```

- [ ] **Step 3: Write `tests/test_anthropic_client_smoke.py`** (skipped unless key present)

```python
import os

import pytest

from deckgen.config import Config
from deckgen.llm.anthropic_client import AnthropicClient
from deckgen.llm.client import LLMRequest


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="no API key")
async def test_smoke_complete():
    client = AnthropicClient(Config.from_env())
    resp = await client.complete(LLMRequest(system="reply with the single word PONG", user="ping", max_tokens=20))
    assert "PONG" in resp.text.upper()
```

- [ ] **Step 4: Run; verify import-only success**

Run: `pytest tests/test_anthropic_client_smoke.py -v`
Expected: 1 skipped (or passed if a key is present).

- [ ] **Step 5: Commit**

```bash
git add src/deckgen/llm/ tests/test_anthropic_client_smoke.py
git commit -m "feat(llm): LLMClient protocol + Anthropic implementation"
```

---

## Task 10: FakeLLMClient for tests

**Files:**
- Create: `src/deckgen/llm/fake_client.py`
- Test: `tests/test_fake_client.py`

- [ ] **Step 1: Write `src/deckgen/llm/fake_client.py`**

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from deckgen.llm.client import LLMRequest, LLMResponse


@dataclass
class FakeLLMClient:
    """Deterministic LLM stand-in for tests.

    Pass a callable that maps an LLMRequest to a string response,
    or a dict keyed on a substring of the system prompt.
    """
    responder: Callable[[LLMRequest], str] | dict[str, str] | None = None
    calls: list[LLMRequest] = field(default_factory=list)

    async def complete(self, req: LLMRequest) -> LLMResponse:
        self.calls.append(req)
        if callable(self.responder):
            return LLMResponse(text=self.responder(req))
        if isinstance(self.responder, dict):
            for key, val in self.responder.items():
                if key in req.system:
                    return LLMResponse(text=val)
        return LLMResponse(text="")
```

- [ ] **Step 2: Write `tests/test_fake_client.py`**

```python
from deckgen.llm.client import LLMRequest
from deckgen.llm.fake_client import FakeLLMClient


async def test_fake_dict_routing():
    fake = FakeLLMClient(responder={"planner": "outline\n", "verifier": '{"verdict":"pass"}'})
    r1 = await fake.complete(LLMRequest(system="you are the planner", user="x"))
    r2 = await fake.complete(LLMRequest(system="you are the verifier", user="y"))
    assert r1.text == "outline\n"
    assert r2.text.startswith("{")
    assert len(fake.calls) == 2
```

- [ ] **Step 3: Run**

Run: `pytest tests/test_fake_client.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/deckgen/llm/fake_client.py tests/test_fake_client.py
git commit -m "test(llm): deterministic FakeLLMClient"
```

---

## Task 11: Prompt files

**Files:**
- Create: `src/deckgen/prompts/clarifier.md`
- Create: `src/deckgen/prompts/planner.md`
- Create: `src/deckgen/prompts/researcher.md`
- Create: `src/deckgen/prompts/card_generator.md`
- Create: `src/deckgen/prompts/card_verifier.md`

Prompts are kept terse — only what materially constrains behavior.

Each prompt opens with `Role: <role>` so the orchestrator and tests can identify which agent is being called by inspecting the system prompt.

- [ ] **Step 1: Write `clarifier.md`**

```markdown
Role: clarifier.

You write follow-up questions for a flashcard deck request.

Inputs (in the user message): topic, size, requested export formats.

Return STRICT JSON only:
{"questions": [{"id": "<slug>", "question": "<text>", "type": "free" | "choice", "options": ["..."]?}]}

Ask 2–4 questions whose answers would change the cards. Skip anything implied by the topic.
```

- [ ] **Step 2: Write `planner.md`**

```markdown
Role: planner.

You produce a card outline for a flashcard deck.

Inputs (in the user message): topic, size N, clarification answers.

Return exactly N lines, one card per line, ≤80 chars each, format:
NNN. <prompt/concept> → <answer hint>

Cards should be non-overlapping and collectively cover the topic.
```

- [ ] **Step 3: Write `researcher.md`**

```markdown
Role: researcher.

You annotate a card outline with source facts and optional images.

Tool: web_search. Use it judiciously; one search may inform many cards.

Return STRICT JSON only:
{"cards": [{"index": <int>, "facts": ["..."], "image_url": "<url>" | null}]}

Keep facts ≤3 per card, ≤30 words each. Only include image_url when the card front would benefit from a picture.
```

- [ ] **Step 4: Write `card_generator.md`**

```markdown
Role: card_generator.

You write one flashcard in markdown.

Inputs (in the user message): outline line, research facts, deck clarification answers, optional local image path, optional critique from a prior review.

Output ONLY the markdown card, in this exact format:

<front markdown>

---

<back markdown>

Tags: #tag1 #tag2

Rules:
- Front asks one unambiguous question. No giveaways.
- Back is tight: one sentence answer + at most one sentence of elaboration.
- Tags line optional; only include if tags are meaningful.
- If a local image path was given, reference it as ![](images/<filename>) on the front.
```

- [ ] **Step 5: Write `card_verifier.md`**

```markdown
Role: card_verifier.

You verify a single flashcard.

Inputs: the card markdown, the outline line it was generated from, and the research facts.

Return STRICT JSON only:
{"verdict": "pass" | "fail", "severity": "low" | "medium" | "high", "issues": ["..."]}

Check in order: format parseable, factuality against research facts, pedagogy (single answer, no giveaway, tight back), scope match. Fail only on real problems.
```

- [ ] **Step 6: Commit**

```bash
git add src/deckgen/prompts/
git commit -m "feat(prompts): terse role prompts for all five agents"
```

---

## Task 12: Pipeline — clarify stage

**Files:**
- Create: `src/deckgen/pipeline/__init__.py`
- Create: `src/deckgen/pipeline/clarify.py`
- Test: `tests/test_pipeline_clarify.py`

The clarify stage has two concerns: (a) the fixed stage-1 questions (asked by the orchestrator, not the LLM) and (b) the LLM-generated adaptive follow-ups. This module owns (b); the orchestrator owns (a).

- [ ] **Step 1: Write failing test**

```python
import json

from deckgen.config import PROMPTS_DIR
from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.clarify import generate_follow_ups


async def test_generate_follow_ups_parses_json():
    payload = {
        "questions": [
            {"id": "scope", "question": "UN only?", "type": "choice", "options": ["yes", "no"]},
            {"id": "back", "question": "Country name on back?", "type": "free"},
        ]
    }
    fake = FakeLLMClient(responder=lambda req: json.dumps(payload))
    qs = await generate_follow_ups(fake, topic="Flags of Africa", size=60, formats=["mochi"])
    assert len(qs) == 2
    assert qs[0].id == "scope"
    assert qs[0].options == ["yes", "no"]
```

- [ ] **Step 2: Implement `src/deckgen/pipeline/__init__.py`** (empty) and `src/deckgen/pipeline/clarify.py`

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from deckgen.config import PROMPTS_DIR
from deckgen.llm.client import LLMClient, LLMRequest


@dataclass
class FollowUp:
    id: str
    question: str
    type: str
    options: list[str] | None = None


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


async def generate_follow_ups(
    client: LLMClient, *, topic: str, size: int, formats: list[str]
) -> list[FollowUp]:
    user = json.dumps({"topic": topic, "size": size, "formats": formats})
    resp = await client.complete(LLMRequest(system=_load_prompt("clarifier"), user=user, max_tokens=1024, temperature=0.3))
    data = json.loads(resp.text)
    return [
        FollowUp(id=q["id"], question=q["question"], type=q["type"], options=q.get("options"))
        for q in data["questions"]
    ]
```

- [ ] **Step 3: Run; verify pass**

Run: `pytest tests/test_pipeline_clarify.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/deckgen/pipeline/__init__.py src/deckgen/pipeline/clarify.py tests/test_pipeline_clarify.py
git commit -m "feat(pipeline): clarifier follow-up generator"
```

---

## Task 13: Pipeline — plan stage

**Files:**
- Create: `src/deckgen/pipeline/plan.py`
- Test: `tests/test_pipeline_plan.py`

- [ ] **Step 1: Write failing test**

```python
from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.plan import generate_outline


async def test_generate_outline_returns_one_line_per_card():
    fake = FakeLLMClient(responder=lambda req: "\n".join(
        [f"{i:03d}. card {i} → ans" for i in range(1, 6)]
    ))
    outline = await generate_outline(fake, topic="X", size=5, follow_ups={})
    assert len(outline) == 5
    assert outline[0].index == 1
    assert outline[4].hint_text.startswith("card 5")
```

- [ ] **Step 2: Implement `src/deckgen/pipeline/plan.py`**

```python
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from deckgen.llm.client import LLMClient, LLMRequest
from deckgen.pipeline.clarify import _load_prompt

LINE_RE = re.compile(r"^\s*(\d{1,4})\.\s*(.+?)\s*$")


@dataclass
class OutlineCard:
    index: int
    hint_text: str  # the post-"NNN. " text, including "→ answer hint"


async def generate_outline(
    client: LLMClient, *, topic: str, size: int, follow_ups: dict[str, str]
) -> list[OutlineCard]:
    user = json.dumps({"topic": topic, "size": size, "answers": follow_ups})
    resp = await client.complete(LLMRequest(system=_load_prompt("planner"), user=user, max_tokens=4096, temperature=0.5))
    out: list[OutlineCard] = []
    for line in resp.text.splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        out.append(OutlineCard(index=int(m.group(1)), hint_text=m.group(2)))
    return out
```

- [ ] **Step 3: Run; verify pass**

Run: `pytest tests/test_pipeline_plan.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/deckgen/pipeline/plan.py tests/test_pipeline_plan.py
git commit -m "feat(pipeline): plan stage produces approved outline"
```

---

## Task 14: Pipeline — research stage

**Files:**
- Create: `src/deckgen/pipeline/research.py`
- Test: `tests/test_pipeline_research.py`

- [ ] **Step 1: Write failing test**

```python
import json

from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.plan import OutlineCard
from deckgen.pipeline.research import research_outline


async def test_research_attaches_facts_and_images():
    payload = {
        "cards": [
            {"index": 1, "facts": ["red disc on white"], "image_url": "https://example.com/jp.png"},
            {"index": 2, "facts": ["tricolour"], "image_url": None},
        ]
    }
    fake = FakeLLMClient(responder=lambda req: json.dumps(payload))
    outline = [OutlineCard(1, "Japan → name"), OutlineCard(2, "France → name")]
    res = await research_outline(fake, outline=outline, topic="Flags")
    assert res[1].facts == ["red disc on white"]
    assert res[1].image_url == "https://example.com/jp.png"
    assert res[2].image_url is None
```

- [ ] **Step 2: Implement `src/deckgen/pipeline/research.py`**

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field

from deckgen.llm.client import LLMClient, LLMRequest
from deckgen.pipeline.clarify import _load_prompt
from deckgen.pipeline.plan import OutlineCard


@dataclass
class ResearchedCard:
    outline: OutlineCard
    facts: list[str] = field(default_factory=list)
    image_url: str | None = None


async def research_outline(
    client: LLMClient, *, outline: list[OutlineCard], topic: str
) -> dict[int, ResearchedCard]:
    user = json.dumps({"topic": topic, "outline": [{"index": c.index, "hint": c.hint_text} for c in outline]})
    resp = await client.complete(
        LLMRequest(system=_load_prompt("researcher"), user=user, tools=["web_search"], max_tokens=8192, temperature=0.3)
    )
    data = json.loads(resp.text)
    by_index = {c.index: c for c in outline}
    out: dict[int, ResearchedCard] = {}
    for c in outline:
        out[c.index] = ResearchedCard(outline=c)
    for item in data.get("cards", []):
        idx = item["index"]
        if idx in out:
            out[idx].facts = item.get("facts", [])
            out[idx].image_url = item.get("image_url")
    return out
```

- [ ] **Step 3: Run; verify pass**

Run: `pytest tests/test_pipeline_research.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/deckgen/pipeline/research.py tests/test_pipeline_research.py
git commit -m "feat(pipeline): research stage with web_search annotations"
```

---

## Task 15: Pipeline — generate stage (parallel)

**Files:**
- Create: `src/deckgen/pipeline/generate.py`
- Test: `tests/test_pipeline_generate.py`

- [ ] **Step 1: Write failing test**

```python
from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.generate import generate_cards
from deckgen.pipeline.plan import OutlineCard
from deckgen.pipeline.research import ResearchedCard


async def test_generate_writes_one_md_per_card(tmp_path):
    def responder(req):
        # Echo a tiny valid card; orchestrator passes the outline in user payload.
        return "Q?\n\n---\n\nA"
    fake = FakeLLMClient(responder=responder)

    outline = [OutlineCard(i, f"item {i}") for i in (1, 2, 3)]
    researched = {c.index: ResearchedCard(outline=c) for c in outline}
    out_dir = tmp_path / "cards"
    written = await generate_cards(
        fake, outline=outline, researched=researched, follow_ups={}, out_dir=out_dir, concurrency=3,
    )
    assert len(written) == 3
    assert (out_dir / "card-001.md").read_text().startswith("Q?")
    assert (out_dir / "card-003.md").exists()
```

- [ ] **Step 2: Implement `src/deckgen/pipeline/generate.py`**

```python
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from deckgen.llm.client import LLMClient, LLMRequest
from deckgen.pipeline.clarify import _load_prompt
from deckgen.pipeline.plan import OutlineCard
from deckgen.pipeline.research import ResearchedCard


def _filename(index: int, total: int) -> str:
    width = max(3, len(str(total)))
    return f"card-{index:0{width}d}.md"


async def _generate_one(
    client: LLMClient,
    outline: OutlineCard,
    researched: ResearchedCard,
    follow_ups: dict[str, str],
    image_filename: str | None,
    critique: str | None,
) -> str:
    user = json.dumps({
        "outline_line": f"{outline.index:03d}. {outline.hint_text}",
        "facts": researched.facts,
        "answers": follow_ups,
        "image_filename": image_filename,
        "critique": critique,
    })
    resp = await client.complete(LLMRequest(system=_load_prompt("card_generator"), user=user, max_tokens=2048))
    return resp.text.strip() + "\n"


async def generate_cards(
    client: LLMClient,
    *,
    outline: list[OutlineCard],
    researched: dict[int, ResearchedCard],
    follow_ups: dict[str, str],
    out_dir: Path,
    concurrency: int,
    image_filenames: dict[int, str] | None = None,
) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(concurrency)
    image_filenames = image_filenames or {}
    total = len(outline)

    async def worker(o: OutlineCard) -> Path:
        async with sem:
            text = await _generate_one(
                client, o, researched[o.index], follow_ups, image_filenames.get(o.index), critique=None
            )
        path = out_dir / _filename(o.index, total)
        path.write_text(text, encoding="utf-8")
        return path

    return await asyncio.gather(*(worker(o) for o in outline))
```

- [ ] **Step 3: Run; verify pass**

Run: `pytest tests/test_pipeline_generate.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/deckgen/pipeline/generate.py tests/test_pipeline_generate.py
git commit -m "feat(pipeline): parallel card generation"
```

---

## Task 16: Pipeline — verify stage (parallel + regen)

**Files:**
- Create: `src/deckgen/pipeline/verify.py`
- Test: `tests/test_pipeline_verify.py`

- [ ] **Step 1: Write failing test**

```python
import json
from pathlib import Path

from deckgen.llm.client import LLMRequest
from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.generate import _filename
from deckgen.pipeline.plan import OutlineCard
from deckgen.pipeline.research import ResearchedCard
from deckgen.pipeline.verify import verify_cards


async def test_verify_passes_through_when_all_pass(tmp_path):
    out_dir = tmp_path
    for i in (1, 2):
        (out_dir / _filename(i, 2)).write_text("Q\n---\nA\n", encoding="utf-8")
    fake = FakeLLMClient(responder=lambda req: '{"verdict":"pass","severity":"low","issues":[]}')
    outline = [OutlineCard(1, "a"), OutlineCard(2, "b")]
    researched = {c.index: ResearchedCard(outline=c) for c in outline}
    report = await verify_cards(
        fake, generator=fake, outline=outline, researched=researched, follow_ups={},
        out_dir=out_dir, concurrency=2, regen=1,
    )
    assert all(r.final_verdict == "pass" for r in report)


async def test_verify_triggers_regen_then_keeps_last(tmp_path):
    out_dir = tmp_path
    (out_dir / _filename(1, 1)).write_text("bad\n---\nbad\n", encoding="utf-8")
    outline = [OutlineCard(1, "x")]
    researched = {1: ResearchedCard(outline=outline[0])}

    verifier_responses = iter([
        '{"verdict":"fail","severity":"high","issues":["wrong"]}',
        '{"verdict":"pass","severity":"low","issues":[]}',
    ])

    def vresponder(req: LLMRequest) -> str:
        if "verifier" in req.system:
            return next(verifier_responses)
        # generator response (regen)
        return "fixed\n---\nfixed\n"

    fake = FakeLLMClient(responder=vresponder)
    report = await verify_cards(
        fake, generator=fake, outline=outline, researched=researched, follow_ups={},
        out_dir=out_dir, concurrency=1, regen=1,
    )
    assert report[0].final_verdict == "pass"
    assert "fixed" in (out_dir / _filename(1, 1)).read_text()
```

- [ ] **Step 2: Implement `src/deckgen/pipeline/verify.py`**

```python
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path

from deckgen.llm.client import LLMClient, LLMRequest
from deckgen.pipeline.clarify import _load_prompt
from deckgen.pipeline.generate import _filename, _generate_one
from deckgen.pipeline.plan import OutlineCard
from deckgen.pipeline.research import ResearchedCard


@dataclass
class CardReport:
    index: int
    attempts: int
    final_verdict: str
    issues: list[str] = field(default_factory=list)


async def _verify_one(client: LLMClient, card_text: str, outline: OutlineCard, facts: list[str]) -> dict:
    user = json.dumps({"card": card_text, "outline_line": f"{outline.index:03d}. {outline.hint_text}", "facts": facts})
    resp = await client.complete(LLMRequest(system=_load_prompt("card_verifier"), user=user, max_tokens=1024, temperature=0.2))
    try:
        return json.loads(resp.text)
    except json.JSONDecodeError:
        return {"verdict": "fail", "severity": "high", "issues": ["verifier returned non-JSON"]}


async def verify_cards(
    client: LLMClient,
    *,
    generator: LLMClient,
    outline: list[OutlineCard],
    researched: dict[int, ResearchedCard],
    follow_ups: dict[str, str],
    out_dir: Path,
    concurrency: int,
    regen: int,
    image_filenames: dict[int, str] | None = None,
) -> list[CardReport]:
    out_dir = Path(out_dir)
    sem = asyncio.Semaphore(concurrency)
    total = len(outline)
    image_filenames = image_filenames or {}

    async def worker(o: OutlineCard) -> CardReport:
        async with sem:
            path = out_dir / _filename(o.index, total)
            text = path.read_text(encoding="utf-8")
            attempts = 1
            verdict = await _verify_one(client, text, o, researched[o.index].facts)
            while verdict.get("verdict") == "fail" and attempts <= regen:
                critique = "; ".join(verdict.get("issues", []))
                new_text = await _generate_one(
                    generator, o, researched[o.index], follow_ups, image_filenames.get(o.index), critique=critique,
                )
                path.write_text(new_text, encoding="utf-8")
                attempts += 1
                verdict = await _verify_one(generator, new_text, o, researched[o.index].facts)
            return CardReport(index=o.index, attempts=attempts, final_verdict=verdict.get("verdict", "fail"), issues=verdict.get("issues", []))

    return await asyncio.gather(*(worker(o) for o in outline))
```

- [ ] **Step 3: Run; verify pass**

Run: `pytest tests/test_pipeline_verify.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/deckgen/pipeline/verify.py tests/test_pipeline_verify.py
git commit -m "feat(pipeline): parallel verification with bounded regeneration"
```

---

## Task 17: Pipeline — export stage wrapper

**Files:**
- Create: `src/deckgen/pipeline/export.py`
- Test: `tests/test_pipeline_export.py`

- [ ] **Step 1: Write failing test**

```python
from pathlib import Path

from deckgen.io.deck_fs import read_deck
from deckgen.pipeline.export import export_deck

FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_export_deck_all_formats_writes_four_files(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_deck(deck, out_root=tmp_path, formats=["mochi", "anki", "markdown", "csv"])
    names = {p.suffix for p in out}
    assert names == {".mochi", ".apkg", ".zip", ".csv"}
    for p in out:
        assert p.parent.name == "Sample"


def test_export_deck_default_mochi_only(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_deck(deck, out_root=tmp_path, formats=["mochi"])
    assert len(out) == 1 and out[0].suffix == ".mochi"


def test_export_deck_all_alias(tmp_path):
    deck = read_deck(FIXTURE)
    out = export_deck(deck, out_root=tmp_path, formats=["all"])
    assert {p.suffix for p in out} == {".mochi", ".apkg", ".zip", ".csv"}
```

- [ ] **Step 2: Implement `src/deckgen/pipeline/export.py`**

```python
from __future__ import annotations

from pathlib import Path

from deckgen.exporters.anki import export_anki
from deckgen.exporters.csv_export import export_csv
from deckgen.exporters.markdown_zip import export_markdown_zip
from deckgen.exporters.mochi import export_mochi
from deckgen.io.deck_fs import Deck

ALL_FORMATS = ("mochi", "anki", "markdown", "csv")
_EXPORTERS = {
    "mochi": export_mochi,
    "anki": export_anki,
    "markdown": export_markdown_zip,
    "csv": export_csv,
}


def export_deck(deck: Deck, *, out_root: Path, formats: list[str]) -> list[Path]:
    if "all" in formats:
        formats = list(ALL_FORMATS)
    out_dir = Path(out_root) / deck.name
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt in formats:
        if fmt not in _EXPORTERS:
            raise ValueError(f"unknown format: {fmt}")
        written.append(_EXPORTERS[fmt](deck, out_dir))
    return written
```

- [ ] **Step 3: Run; verify pass**

Run: `pytest tests/test_pipeline_export.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/deckgen/pipeline/export.py tests/test_pipeline_export.py
git commit -m "feat(pipeline): export stage wrapper supporting all formats"
```

---

## Task 18: Orchestrator + end-to-end test with FakeLLMClient

**Files:**
- Create: `src/deckgen/pipeline/orchestrator.py`
- Test: `tests/test_orchestrator_e2e.py`

The orchestrator is non-interactive at its core (takes already-collected inputs) so it's testable. A separate interactive wrapper in the CLI handles stdin prompting.

- [ ] **Step 1: Write failing test**

```python
import json
from pathlib import Path

from deckgen.llm.client import LLMRequest
from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.orchestrator import GenerationInputs, run_pipeline


async def test_full_pipeline_writes_raw_and_exports(tmp_path):
    def responder(req: LLMRequest) -> str:
        s = req.system
        if "planner" in s:
            return "\n".join(f"{i:03d}. card {i} → ans" for i in range(1, 4))
        if "researcher" in s:
            return json.dumps({"cards": [{"index": i, "facts": [f"fact {i}"], "image_url": None} for i in range(1, 4)]})
        if "verifier" in s:
            return '{"verdict":"pass","severity":"low","issues":[]}'
        # generator
        return "Q\n\n---\n\nA\n"
    fake = FakeLLMClient(responder=responder)

    inputs = GenerationInputs(
        name="Sample",
        topic="Sample topic",
        description="A sample deck",
        size=3,
        formats=["mochi", "csv"],
        follow_ups={},
    )
    result = await run_pipeline(
        client=fake, inputs=inputs,
        decks_raw=tmp_path / "raw", decks_exported=tmp_path / "exported",
        concurrency=2, regen=1,
    )
    raw_dir = tmp_path / "raw" / "Sample"
    assert (raw_dir / "deck.json").exists()
    assert len(list(raw_dir.glob("card-*.md"))) == 3
    exports = list((tmp_path / "exported" / "Sample").iterdir())
    suffixes = {p.suffix for p in exports}
    assert suffixes == {".mochi", ".csv"}
    assert result.report and all(r.final_verdict == "pass" for r in result.report)
```

- [ ] **Step 2: Implement `src/deckgen/pipeline/orchestrator.py`**

```python
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from pathlib import Path

from deckgen.io.deck_fs import read_deck
from deckgen.io.image_fetch import fetch_image
from deckgen.llm.client import LLMClient
from deckgen.pipeline.export import export_deck
from deckgen.pipeline.generate import generate_cards
from deckgen.pipeline.plan import generate_outline
from deckgen.pipeline.research import research_outline
from deckgen.pipeline.verify import CardReport, verify_cards


@dataclass
class GenerationInputs:
    name: str
    topic: str
    description: str
    size: int
    formats: list[str]
    follow_ups: dict[str, str] = field(default_factory=dict)


@dataclass
class GenerationResult:
    raw_folder: Path
    exports: list[Path]
    report: list[CardReport]


def _write_deck_json(folder: Path, inputs: GenerationInputs) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "deck.json").write_text(json.dumps({
        "name": inputs.name,
        "description": inputs.description,
        "created_at": _dt.datetime.utcnow().isoformat() + "Z",
        "generator_version": "0.1.0",
        "source_topic": inputs.topic,
        "follow_up_answers": inputs.follow_ups,
    }, indent=2), encoding="utf-8")


async def run_pipeline(
    *,
    client: LLMClient,
    inputs: GenerationInputs,
    decks_raw: Path,
    decks_exported: Path,
    concurrency: int,
    regen: int,
    overwrite: bool = False,
    append: bool = False,
) -> GenerationResult:
    raw_folder = Path(decks_raw) / inputs.name
    if raw_folder.exists() and not (overwrite or append):
        raise FileExistsError(
            f"{raw_folder} already exists. Use --overwrite to replace or --append to add cards."
        )
    if overwrite and raw_folder.exists():
        import shutil
        shutil.rmtree(raw_folder)
    _write_deck_json(raw_folder, inputs)

    outline = await generate_outline(client, topic=inputs.topic, size=inputs.size, follow_ups=inputs.follow_ups)
    researched = await research_outline(client, outline=outline, topic=inputs.topic)

    images_dir = raw_folder / "images"
    image_filenames: dict[int, str] = {}
    for idx, rc in researched.items():
        if rc.image_url:
            p = fetch_image(rc.image_url, images_dir)
            if p is not None:
                image_filenames[idx] = p.name

    await generate_cards(
        client, outline=outline, researched=researched, follow_ups=inputs.follow_ups,
        out_dir=raw_folder, concurrency=concurrency, image_filenames=image_filenames,
    )
    report = await verify_cards(
        client, generator=client, outline=outline, researched=researched, follow_ups=inputs.follow_ups,
        out_dir=raw_folder, concurrency=concurrency, regen=regen, image_filenames=image_filenames,
    )

    deck = read_deck(raw_folder)
    exports = export_deck(deck, out_root=Path(decks_exported), formats=inputs.formats)
    return GenerationResult(raw_folder=raw_folder, exports=exports, report=report)
```

- [ ] **Step 3: Run; verify pass**

Run: `pytest tests/test_orchestrator_e2e.py -v`
Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add src/deckgen/pipeline/orchestrator.py tests/test_orchestrator_e2e.py
git commit -m "feat(pipeline): orchestrator + end-to-end fake-client test"
```

---

## Task 19: API-mode CLI (`scripts/generate.py`)

**Files:**
- Create: `src/deckgen/cli.py`
- Create: `scripts/generate.py`
- Test: `tests/test_cli_args.py`

- [ ] **Step 1: Write failing test for arg parsing**

```python
from deckgen.cli import build_arg_parser


def test_arg_parser_defaults_and_overrides():
    p = build_arg_parser()
    ns = p.parse_args(["--topic", "Flags", "--size", "60", "--format", "anki", "--format", "csv"])
    assert ns.topic == "Flags"
    assert ns.size == 60
    assert ns.format == ["anki", "csv"]
    assert ns.regen == 1
    assert ns.concurrency == 10
    assert not ns.overwrite
```

- [ ] **Step 2: Implement `src/deckgen/cli.py`**

```python
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from rich.console import Console

from deckgen.config import (
    Config, DECKS_EXPORTED, DECKS_RAW, DEFAULT_CONCURRENCY, DEFAULT_REGEN, DEFAULT_SIZE,
)
from deckgen.llm.anthropic_client import AnthropicClient
from deckgen.pipeline.clarify import generate_follow_ups
from deckgen.pipeline.orchestrator import GenerationInputs, run_pipeline
from deckgen.pipeline.plan import generate_outline

console = Console()


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="deckgen", description="Generate a flashcard deck")
    p.add_argument("--topic")
    p.add_argument("--name")
    p.add_argument("--description", default="")
    p.add_argument("--size", type=int, default=DEFAULT_SIZE)
    p.add_argument("--format", action="append", choices=["mochi", "anki", "markdown", "csv", "all"])
    p.add_argument("--regen", type=int, default=DEFAULT_REGEN)
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--model")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--append", action="store_true")
    p.add_argument("--non-interactive", action="store_true")
    return p


def _ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or (default or "")


async def _interactive_inputs(client, ns) -> GenerationInputs:
    topic = ns.topic or _ask("Deck description (topic + scope)")
    size = ns.size if ns.topic else int(_ask("Size", str(DEFAULT_SIZE)) or DEFAULT_SIZE)
    formats = ns.format or [_ask("Export format (mochi/anki/markdown/csv/all)", "mochi") or "mochi"]
    name = ns.name or _ask("Deck name", topic[:40])

    console.print("[dim]Asking follow-up questions...[/dim]")
    answers: dict[str, str] = {}
    for q in await generate_follow_ups(client, topic=topic, size=size, formats=formats):
        suffix = f" ({'/'.join(q.options)})" if q.options else ""
        answers[q.id] = _ask(f"{q.question}{suffix}")

    console.print("[dim]Drafting outline...[/dim]")
    outline = await generate_outline(client, topic=topic, size=size, follow_ups=answers)
    for c in outline:
        console.print(f"  {c.index:03d}. {c.hint_text}")
    if _ask("Approve outline? (y/n)", "y").lower() != "y":
        console.print("[red]Aborted.[/red]")
        sys.exit(1)

    return GenerationInputs(
        name=name, topic=topic, description=ns.description or topic, size=size, formats=formats, follow_ups=answers,
    )


async def _amain(argv: list[str] | None = None) -> int:
    ns = build_arg_parser().parse_args(argv)
    config = Config.from_env()
    if ns.model:
        config.model = ns.model
    if ns.concurrency:
        config.concurrency = ns.concurrency
    if ns.regen is not None:
        config.regen = ns.regen
    if not config.api_key:
        console.print("[red]ANTHROPIC_API_KEY missing. Copy .env.example to .env and add your key.[/red]")
        return 2

    client = AnthropicClient(config)
    if ns.non_interactive:
        if not ns.topic or not ns.name:
            console.print("[red]--non-interactive requires --topic and --name[/red]")
            return 2
        inputs = GenerationInputs(
            name=ns.name, topic=ns.topic, description=ns.description or ns.topic,
            size=ns.size, formats=ns.format or ["mochi"], follow_ups={},
        )
    else:
        inputs = await _interactive_inputs(client, ns)

    result = await run_pipeline(
        client=client, inputs=inputs,
        decks_raw=DECKS_RAW, decks_exported=DECKS_EXPORTED,
        concurrency=config.concurrency, regen=config.regen,
        overwrite=ns.overwrite, append=ns.append,
    )
    console.print(f"[green]Wrote {len(result.exports)} export(s):[/green]")
    for p in result.exports:
        console.print(f"  {p}")
    fails = [r for r in result.report if r.final_verdict != "pass"]
    if fails:
        console.print(f"[yellow]{len(fails)} card(s) failed verification after regen; see content for review.[/yellow]")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))
```

- [ ] **Step 3: Create `scripts/generate.py` thin shim**

```python
#!/usr/bin/env python3
"""Entry point: python scripts/generate.py [args]"""
from deckgen.cli import main

if __name__ == "__main__":
    main()
```

Run: `chmod +x scripts/generate.py`

- [ ] **Step 4: Run; verify pass**

Run: `pytest tests/test_cli_args.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/deckgen/cli.py scripts/generate.py tests/test_cli_args.py
git commit -m "feat(cli): API-mode generate.py with interactive prompts"
```

---

## Task 20: `scripts/export_only.py`

**Files:**
- Create: `scripts/export_only.py`
- Test: `tests/test_export_only_script.py`

- [ ] **Step 1: Write failing test**

```python
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "sample_deck"


def test_export_only_runs_against_a_raw_folder(tmp_path):
    # Copy fixture to a tmp "raw" location with the deck name "Sample".
    raw = tmp_path / "raw" / "Sample"
    raw.mkdir(parents=True)
    for p in FIXTURE.rglob("*"):
        if p.is_file():
            dest = raw / p.relative_to(FIXTURE)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(p.read_bytes())

    exported = tmp_path / "exported"
    cmd = [sys.executable, str(REPO / "scripts" / "export_only.py"),
           "--name", "Sample",
           "--raw-root", str(tmp_path / "raw"),
           "--exported-root", str(exported),
           "--format", "csv", "--format", "markdown"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    out_dir = exported / "Sample"
    assert (out_dir / "Sample.csv").exists()
    assert (out_dir / "Sample.zip").exists()
```

- [ ] **Step 2: Implement `scripts/export_only.py`**

```python
#!/usr/bin/env python3
"""Re-export an existing raw deck folder without regenerating cards."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from deckgen.config import DECKS_EXPORTED, DECKS_RAW
from deckgen.io.deck_fs import read_deck
from deckgen.pipeline.export import export_deck


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True)
    p.add_argument("--raw-root", default=str(DECKS_RAW))
    p.add_argument("--exported-root", default=str(DECKS_EXPORTED))
    p.add_argument("--format", action="append", choices=["mochi", "anki", "markdown", "csv", "all"])
    ns = p.parse_args()
    deck = read_deck(Path(ns.raw_root) / ns.name)
    out = export_deck(deck, out_root=Path(ns.exported_root), formats=ns.format or ["mochi"])
    for path in out:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `chmod +x scripts/export_only.py`

- [ ] **Step 3: Run; verify pass**

Run: `pytest tests/test_export_only_script.py -v`

- [ ] **Step 4: Commit**

```bash
git add scripts/export_only.py tests/test_export_only_script.py
git commit -m "feat(cli): export_only.py for re-exporting raw decks"
```

---

## Task 21: Claude Code skill + subagents

**Files:**
- Create: `.claude/skills/deck-generation/SKILL.md`
- Create: `.claude/agents/card-generator.md`
- Create: `.claude/agents/card-verifier.md`

The skill instructs Claude how to run the same pipeline using its own tools. The subagents wrap the same prompt files. Skill file uses frontmatter with `name` and `description` per Claude Code skill format.

- [ ] **Step 1: Write `.claude/skills/deck-generation/SKILL.md`**

```markdown
---
name: deck-generation
description: Generate a Mochi/Anki flashcard deck from a topic. Use when the user asks to make a deck, create flashcards, or build study material. Runs an interactive clarify → plan → research → generate → verify → export pipeline using parallel subagents.
---

# Deck generation

You produce a flashcard deck in `decks/raw/<Name>/` and exports in `decks/exported/<Name>/`. The repo root is the current working directory.

## Stage 1 — fixed questions

Ask the user, in order:
1. Description of the deck (topic + scope).
2. Size (integer; default 50).
3. Export format(s): any of `mochi`, `anki`, `markdown`, `csv`, or `all`. Default `mochi`.

## Stage 2 — follow-ups

Read `src/deckgen/prompts/clarifier.md` and ask 2–4 follow-up questions that materially shape the cards. Skip anything implied by the topic.

## Stage 3 — outline + approval

Read `src/deckgen/prompts/planner.md`. Produce a one-line-per-card outline (NNN. prompt → answer hint). Show it to the user and wait for approval.

## Stage 4 — research

Read `src/deckgen/prompts/researcher.md`. Use your `web_search` tool to annotate the outline with source facts and optional image URLs. Download images into `decks/raw/<Name>/images/` via `Bash` (`curl` is fine) before generation.

## Stage 5 — parallel generation

Dispatch one `Agent` tool call per card in a single message, `subagent_type: card-generator`. Each subagent writes its file to `decks/raw/<Name>/card-NNN.md`.

## Stage 6 — parallel verification

Dispatch one `Agent` tool call per card with `subagent_type: card-verifier`. On `fail`, regenerate with the verifier's critique (up to 1 retry by default).

## Stage 7 — export

Run: `python -m deckgen.cli --non-interactive --name <Name> --topic <topic> --format <fmt> [--format <fmt>...]` — or, if cards are already on disk, run `python scripts/export_only.py --name <Name> --format <fmt>`.

Report the final paths to the user.

## Rules

- Refuse to overwrite an existing `decks/raw/<Name>/`. Ask the user to choose a new name or pass overwrite intent.
- Never invent facts; rely on the research stage.
- Keep your own messages terse. Show progress concisely.
```

- [ ] **Step 2: Write `.claude/agents/card-generator.md`**

```markdown
---
name: card-generator
description: Generates a single flashcard for a deck given an outline line and research facts.
tools: Read, Write
---

You write one flashcard. Read `src/deckgen/prompts/card_generator.md` for the role spec and follow it exactly. Write the result to the path provided in your task input.
```

- [ ] **Step 3: Write `.claude/agents/card-verifier.md`**

```markdown
---
name: card-verifier
description: Verifies a single flashcard against research facts and the outline. Returns JSON verdict.
tools: Read
---

You verify one flashcard. Read `src/deckgen/prompts/card_verifier.md` for the role spec and follow it exactly. Return the JSON verdict as your final message.
```

- [ ] **Step 4: Manual smoke (no automated test for skill — it runs inside Claude Code)**

Verify by inspection that the three files exist and parse as markdown with frontmatter.

- [ ] **Step 5: Commit**

```bash
git add .claude/
git commit -m "feat(cc): deck-generation skill + card-generator/verifier subagents"
```

---

## Task 22: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`** — copy-paste-ready, both run paths, with examples.

````markdown
# DeckGeneration

Generate Mochi / Anki flashcard decks from a topic description. Two run modes: a Python script using the Anthropic API, or a Claude Code skill.

## What it does

- Takes a topic ("Flags of Africa, 60 cards") and produces a folder of markdown cards.
- Runs a clarify → plan → research → generate → verify pipeline with parallel agents.
- Exports to `.mochi`, `.apkg` (Anki), markdown zip, and CSV.

## Quickstart

### Option A — API script

```bash
git clone <repo-url> DeckGeneration && cd DeckGeneration
pip install -e .
cp .env.example .env       # paste your ANTHROPIC_API_KEY
python scripts/generate.py
```

Or one-shot:

```bash
python scripts/generate.py \
    --topic "Flags of Africa" --name FlagsAfrica \
    --size 60 --format all --non-interactive
```

### Option B — Claude Code skill

```bash
git clone <repo-url> DeckGeneration && cd DeckGeneration
ln -s "$(pwd)/.claude/skills/deck-generation" ~/.claude/skills/deck-generation
claude                     # opens Claude Code here
> /deck-generation
```

The skill runs the same pipeline using Claude Code's built-in agent dispatch — no API key required.

## What you get

```
decks/raw/<Name>/
    card-001.md ... card-NNN.md   # one card per file, edit by hand if you like
    images/                        # downloaded media
    deck.json                      # metadata
decks/exported/<Name>/
    <Name>.mochi    # import into Mochi: File → Import
    <Name>.apkg     # import into Anki: drag onto Anki Desktop
    <Name>.zip      # markdown zip (Mochi also imports this)
    <Name>.csv
```

## CLI reference (API mode)

| Flag | Default | Notes |
|---|---|---|
| `--topic STR` | (prompted) | Deck description |
| `--name STR` | (prompted) | Folder/deck name |
| `--size INT` | 50 | Number of cards |
| `--format X` | `mochi` | Repeatable; `all` enables every format |
| `--regen INT` | 1 | Max regen attempts per failed verification |
| `--concurrency INT` | 10 | Parallel agents |
| `--model NAME` | `claude-sonnet-4-6` | Anthropic model |
| `--overwrite` | off | Replace existing raw folder |
| `--append` | off | Add cards to existing raw folder |
| `--non-interactive` | off | Skip prompts |

## Customizing prompts

Edit any file in `src/deckgen/prompts/`. Both run modes reload prompts on each run.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

## Troubleshooting

- **`ANTHROPIC_API_KEY missing`** — copy `.env.example` to `.env` and paste your key from console.anthropic.com.
- **Rate limit errors** — lower `--concurrency`. Default is 10.
- **Image fetch failures** — logged as warnings, do not fail the run.
- **Mochi import says invalid file** — try the `.zip` (markdown) export instead; Mochi accepts both.

## License

MIT.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with both run paths and CLI reference"
```

---

## Final verification

- [ ] **Step 1: Run the full test suite**

Run: `pytest -v`
Expected: all tests pass; only `test_anthropic_client_smoke.py` may skip without a key.

- [ ] **Step 2: Manual smoke (if key available)**

```bash
python scripts/generate.py --topic "Capitals of Europe" --name TestCapitals \
    --size 5 --format csv --non-interactive
ls decks/raw/TestCapitals/
ls decks/exported/TestCapitals/
```

- [ ] **Step 3: Tag a release**

```bash
git tag v0.1.0
```

---

## Spec coverage check

- §3 architecture → Task 18 orchestrator + Tasks 12–17 stages.
- §4 repo layout → Task 1 scaffold + all later tasks fill in directories.
- §5 run paths → Task 19 (script), Task 21 (skill).
- §5.3 CLI flags → Task 19 (`build_arg_parser` covers all flags).
- §6 prompt flow → Task 19 `_interactive_inputs` for stage 1 + 2 + 3; Task 21 skill mirrors the same flow.
- §7.1 card format → Task 2 parser + Task 11 generator prompt.
- §7.2 exporters → Tasks 5–8 + Task 17 wrapper.
- §8 prompts and agents → Task 11 + Task 21.
- §9 error handling → Task 9 retry/backoff; Task 18 refusal on existing folder; Task 4 image fetch returns `None` on failure.
- §10 testing → fixtures in Task 2; tests interleaved through every task; end-to-end in Task 18.
- §11 README → Task 22.
- §12 dependencies → Task 1 `pyproject.toml`.
