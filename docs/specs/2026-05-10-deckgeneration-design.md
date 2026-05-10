# DeckGeneration — Design Spec

**Date:** 2026-05-10
**Status:** Approved, ready for implementation planning

## 1. Purpose

A self-contained tool that turns a topic description into a spaced-repetition deck. A user clones the repo and, with either an Anthropic API key or a Claude Code subscription, produces ready-to-import decks for Mochi and Anki.

Raw decks live as folders of markdown files on disk (one card per file, `---` separates front from back) so they are human-editable, diffable in git, and serve as a portable source format. The same raw folder can be exported to four target formats: Mochi (`.mochi`), Anki (`.apkg`), a markdown zip (also importable into Mochi), and CSV.

## 2. Goals and non-goals

**Goals**
- Anyone who clones the repo can produce a usable deck within minutes via one of two entry points.
- Two distinct ways to run the pipeline: (a) a Python script that talks to the Anthropic API, (b) a Claude Code skill installed locally.
- Interactive prompt flow with fixed initial questions plus LLM-generated adaptive follow-ups.
- Plan-then-approve workflow before any expensive parallel card generation.
- Parallel card generation and parallel verification, with bounded regeneration on rejected cards.
- Same prompts, same pipeline logic, same on-disk artifacts regardless of run mode.

**Non-goals (v1)**
- Hosted UI; spaced-repetition scheduling; auto-publishing to Mochi/Anki cloud; multi-LLM provider abstraction (Anthropic only); custom card templates beyond Basic front/back; image generation (we fetch existing images, we do not generate them).

## 3. Architecture overview

A Python package (`src/deckgen/`) implements the pipeline. Two entry points share the same orchestration core:

```
generate_deck()  ← orchestrator (shared core)
   │
   ├─ API mode:  scripts/generate.py          (Anthropic SDK client)
   └─ CC mode:   .claude/skills/              (Claude Code skill,
                 deck-generation/SKILL.md      uses Agent tool for
                                               parallel subagents)
```

An `LLMClient` protocol abstracts over Anthropic SDK calls (API mode) and Claude Code's native agent dispatch (CC mode). Both implementations consume the same prompt files in `src/deckgen/prompts/`.

Pipeline stages, one module per stage in `src/deckgen/pipeline/`:

1. `clarify.py` — interactive question loop (fixed questions then adaptive follow-ups)
2. `plan.py` — LLM produces a compressed card outline; user approves
3. `research.py` — single LLM call with web search; annotates each outline line with source facts and optional image URLs
4. `generate.py` — fan out N CardGenerator workers in parallel, one card per worker; writes `decks/raw/<Name>/card-NNN.md`
5. `verify.py` — fan out N CardVerifier workers in parallel; on `fail`, regenerate the card with the verifier's critique, up to `--regen` times
6. `export.py` — convert the raw folder into one or more target formats in `decks/exported/<Name>/`

## 4. Repo layout

```
DeckGeneration/
├── README.md                          # what it is, install, both run paths, examples
├── pyproject.toml                     # package metadata, deps, console script entry
├── .env.example                       # ANTHROPIC_API_KEY=...
├── .gitignore                         # .env, decks/raw/*, decks/exported/*, __pycache__
│
├── src/deckgen/
│   ├── __init__.py
│   ├── config.py                      # env loading, model names, defaults
│   ├── llm/
│   │   ├── client.py                  # LLMClient protocol
│   │   ├── anthropic_client.py        # API-mode implementation (SDK + web_search tool)
│   │   └── claude_code_client.py      # CC-mode implementation
│   ├── pipeline/
│   │   ├── orchestrator.py            # ties stages together, prints progress
│   │   ├── clarify.py
│   │   ├── plan.py
│   │   ├── research.py
│   │   ├── generate.py
│   │   ├── verify.py
│   │   └── export.py
│   ├── prompts/                       # one .md per agent role, loaded at runtime
│   │   ├── clarifier.md
│   │   ├── planner.md
│   │   ├── researcher.md
│   │   ├── card_generator.md
│   │   └── card_verifier.md
│   ├── exporters/
│   │   ├── mochi.py
│   │   ├── anki.py
│   │   ├── markdown_zip.py
│   │   └── csv.py
│   └── io/
│       ├── deck_fs.py                 # read/write raw card files, image dir
│       └── image_fetch.py             # httpx download → decks/raw/<Name>/images/
│
├── scripts/
│   ├── generate.py                    # API-mode entry point
│   └── export_only.py                 # convert an existing decks/raw/<Name>/ to exports
│
├── .claude/
│   ├── skills/
│   │   └── deck-generation/
│   │       └── SKILL.md               # the installable skill
│   └── agents/
│       ├── card-generator.md          # subagent definition (CC mode)
│       └── card-verifier.md           # subagent definition (CC mode)
│
├── decks/
│   ├── raw/                           # one folder per deck, gitignored
│   │   └── .gitkeep
│   └── exported/                      # one folder per deck, gitignored
│       └── .gitkeep
│
└── tests/
    ├── test_export_mochi.py
    ├── test_export_anki.py
    ├── test_export_csv.py
    ├── test_export_markdown_zip.py
    ├── test_parse_card.py
    ├── test_pipeline_orchestrator.py
    └── fixtures/sample_deck/
```

Notes on layout choices:
- Prompts are `.md` files, not Python strings — editable without code changes, and the CC-mode skill reads the same files.
- `decks/` is gitignored so generated decks do not pollute the repo when others clone it.
- Both run paths import `src/deckgen/` — the skill has full Bash/Python access in Claude Code.

## 5. Run paths

### 5.1 API mode (script + Anthropic API key)

```bash
git clone <repo> && cd DeckGeneration
pip install -e .
cp .env.example .env                   # paste ANTHROPIC_API_KEY
python scripts/generate.py             # interactive
# or one-shot:
python scripts/generate.py --topic "Flags of Africa" --size 60 --format mochi
```

### 5.2 Claude Code mode (skill, no API key)

```bash
git clone <repo> && cd DeckGeneration
ln -s "$(pwd)/.claude/skills/deck-generation" ~/.claude/skills/deck-generation
claude
> /deckgen
```

The skill's `SKILL.md` instructs Claude to run the same pipeline using its built-in `Agent`, `Bash`, and `Write` tools. Parallel card generation uses parallel `Agent` tool calls (Claude Code dispatches them concurrently). Subagent definitions live in `.claude/agents/`.

Both modes write to the same `decks/raw/<Name>/` and `decks/exported/<Name>/` locations. A user can generate in one mode and re-export from the other.

### 5.3 CLI flags (API mode)

- `--topic STRING` `--size INT` `--name STRING`
- `--format mochi|anki|markdown|csv|all` (repeatable; default `mochi`)
- `--regen INT` (default `1`) — max regeneration attempts per rejected card
- `--concurrency INT` (default `10`)
- `--overwrite` / `--append` (default: refuse if `decks/raw/<Name>/` exists)
- `--non-interactive` — skip prompts; use the flags as-is
- `--model claude-opus-4-7|claude-sonnet-4-6` (default `claude-sonnet-4-6`)

## 6. Interactive prompt flow

Identical in both modes. The orchestrator prints/asks on stdin in script mode and posts chat messages in skill mode.

**Stage 1 — fixed questions:**
1. *Description of the deck* — free text. Example: "capital cities of African countries, focusing on the 54 UN members".
2. *Size* — integer. Default `50`.
3. *Export format* — one or more of `mochi` / `anki` / `markdown` / `csv` / `all`. Default `mochi`. `all` produces every format.

**Stage 2 — adaptive follow-ups:**
The `clarifier` agent receives the stage-1 answers and returns 2–4 follow-up questions whose answers would materially change the cards. Examples:
- For "Flags of Africa, 60 cards": *"Include territories and disputed regions, or UN members only?"*; *"Front shows flag image, back shows country — or swap?"*; *"Tag by region?"*
- For "French Revolution dates, 30 cards": *"Cloze deletions or front-question / back-date?"*; *"Strict 1789–1799 or include lead-up?"*

**Stage 3 — outline approval:**
The `planner` produces a compressed outline (one line per card, ≤80 chars). The orchestrator prints it and asks `[a]pprove / [e]dit / [r]egenerate`. No expensive work begins until the outline is approved.

After approval: research (single call) → parallel generate → parallel verify → export. Progress is reported inline (e.g. `[research ✓] [generate 47/60] [verify 23/60 — 2 regen]`).

## 7. Card and deck formats

### 7.1 Raw card file (`decks/raw/<DeckName>/card-NNN.md`)

```markdown
What country has this flag?

![](images/jp.png)

---

Japan

Adopted 1999. The red disc represents the sun.

Tags: #asia #island-nations
```

Rules:
- Filename `card-NNN.md`, zero-padded to the width of the total count.
- The **first** `---` line separates front from back. Subsequent `---` lines are literal content.
- Markdown is allowed on both sides (lists, bold, code, math `$…$` / `$$…$$`).
- Images: `![alt](images/<file>)`. Files live in `decks/raw/<DeckName>/images/`.
- Optional final line on the back matching `^Tags: (#\w+\s*)+$` is parsed as deck tags.
- Each deck folder includes `deck.json`: `{name, description, created_at, generator_version, source_topic, follow_up_answers}`.

Parser at `src/deckgen/io/deck_fs.py`:
- `read_card(path) -> Card`
- `read_deck(folder) -> Deck`
- `Card` dataclass fields: `front_md`, `back_md`, `tags`, `image_paths`

This is the single source of truth consumed by every exporter.

### 7.2 Exporters

All exporters write into `decks/exported/<DeckName>/` side-by-side when `--format all`.

- **`mochi.py`** → `<Name>.mochi` (zip). Contents:
  - `data.edn` in Mochi's deck format. Schema sketch: `{:version 2 :decks [{:id … :name … :cards [{:id … :name … :content "<front>\n---\n<back>" :deck-id …}]}]}`. Markdown bodies preserved verbatim.
  - Images at top level. Image links rewritten to Mochi attachment syntax (`![](@image-id)`).
  - EDN is hand-written; the subset we use is small.
- **`anki.py`** → `<Name>.apkg`. Uses `genanki` with one `Model` (Basic front/back/tags) and one `Note` per card. Images attached via `Package.media_files`. `genanki` model_id is a stable hash of the deck name so re-exports are deterministic.
- **`markdown_zip.py`** → `<Name>.zip` of the raw folder. Mochi also imports this format as a fallback.
- **`csv.py`** → `front,back,tags` with multi-line cells quoted. Images skipped with a warning.

## 8. Prompts and agent design

Five prompt files in `src/deckgen/prompts/`, each a markdown file with role description, instructions, and I/O contract. Loaded at runtime.

- **`clarifier.md`** — single call. Input: `{topic, size, formats}`. Output: JSON `{"questions": [{"id", "question", "type": "free|choice", "options"?}]}`, 2–4 items. Skip questions whose answer is implied by the topic.
- **`planner.md`** — single call. Takes topic + size + clarification answers. Returns a compressed card outline, one line per card, ≤80 chars. This is the artifact the user approves.
- **`researcher.md`** — single call with Anthropic's `web_search` tool enabled. Takes the approved outline. Returns the outline annotated with `source_facts` (≤3 bullets) and optional `image_url` per card. The orchestrator downloads images locally before generators run.
- **`card_generator.md`** — runs N in parallel, once per card. Input: one outline line + research annotations + clarification answers. Output: a single markdown card matching §7.1. Constraints: front asks one unambiguous question; back is tight (1 sentence + optional 1-sentence elaboration); tags drawn from a deck-level tag vocabulary the planner produced.
- **`card_verifier.md`** — runs N in parallel. Input: card markdown + outline line + research annotations. Output: JSON `{"verdict": "pass|fail", "issues": [...], "severity": "low|medium|high"}`. Checks in order: format parseability, factuality against research annotations, pedagogy (unambiguous front, tight back, no giveaway), scope match. On `fail`, the orchestrator regenerates with the verifier's `issues` as critique, up to `--regen` times.

### 8.1 Dispatch

- **API mode**: `asyncio.gather` with a `Semaphore(concurrency)`. Each task is one Anthropic API call. Exponential backoff with jitter on 429 / 529, max 5 retries.
- **CC mode**: the skill issues parallel `Agent` tool calls in a single message; Claude Code dispatches them concurrently. The subagent definitions in `.claude/agents/` reference the same prompt files.

## 9. Error handling

Only at boundaries that actually fail:
- `ANTHROPIC_API_KEY` missing → exit with a single message pointing at `.env.example`.
- `decks/raw/<Name>/` already exists → refuse with the three flag options (`--overwrite` / `--append` / new name).
- API 429 / 529 → exponential backoff with jitter, max 5 retries, then bubble up.
- Image fetch fails → log a warning, skip the image, continue.
- Card parse fails after final regen → write the text to `card-NNN.md.broken` and log. Exporters skip `.broken` files with a warning.
- `scripts/export_only.py <Name>` is idempotent and safe to re-run against an existing raw folder.

## 10. Testing

`pytest`, no network calls.

- `test_parse_card.py` — round-trip parse of the sample deck; multiple `---`, images, math, missing tags line.
- `test_export_mochi.py` — open the produced zip, validate `data.edn` parses and contains every card, check image rewrites.
- `test_export_anki.py` — assert deck has expected card count and media files; deterministic via stable `model_id`.
- `test_export_csv.py` — string equality against a fixture.
- `test_export_markdown_zip.py` — zip contents match raw folder.
- `test_pipeline_orchestrator.py` — `FakeLLMClient` returns canned responses; the test runs the full pipeline against a tmp dir and asserts the four exporters produce expected files.

`tests/fixtures/sample_deck/` is a 3-card hand-written deck (image card, math card, plain card).

## 11. README outline

The README is the front door. Structure:

1. One-line description + screenshot.
2. **What it does** — 3 bullets, mention Mochi and Anki.
3. **Quickstart** — both options side by side:
   - Option A: API script with copy-pasteable commands.
   - Option B: Claude Code skill with install command and `/deckgen` example.
4. **Example: build a Flags deck end-to-end** — walk through one run from clarify to import.
5. **Outputs** — explain `decks/raw/` and `decks/exported/`.
6. **Importing into apps** — Mochi import steps, Anki import steps.
7. **CLI reference** — every flag from §5.3.
8. **Configuration** — `.env` vars, switching models, defaults in `src/deckgen/config.py`.
9. **Customizing prompts** — edit `src/deckgen/prompts/*.md`; both modes pick up changes.
10. **Troubleshooting** — rate limits, missing key, image download failures, import errors.
11. **How it works** — one diagram of the six pipeline stages.
12. **Development** — `pip install -e ".[dev]"`, `pytest`, project layout.
13. **License.**

## 12. Dependencies

Runtime: `anthropic`, `httpx`, `python-dotenv`, `genanki`, `pydantic`, `rich`.
Dev: `pytest`, `pytest-asyncio`, `ruff`.

## 13. Open questions

None at design approval. To be revisited during implementation:
- Exact EDN schema version Mochi accepts on import — verified against a current Mochi `.mochi` export before finalizing `exporters/mochi.py`.
- Whether the skill should ship as a plugin (`plugin.json`) for one-command install in addition to the symlink path.
