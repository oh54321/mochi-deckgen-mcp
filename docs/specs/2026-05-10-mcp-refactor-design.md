# DeckGen MCP Refactor — Design Spec

**Date:** 2026-05-10
**Status:** Implemented (verify.sh green on 2026-05-10)
**Supersedes:** `docs/specs/2026-05-10-deckgeneration-design.md` (the previous local-pipeline-with-Anthropic-API design)

## 1. Purpose

Refactor the existing `mochi-tools-mcp` project into a Model Context Protocol (MCP) server. The server is the single distribution unit: it ships filesystem primitives, Mochi API primitives, sync primitives, image-processing primitives, subagent prompts, and workflow prompts. Any MCP-capable client (Claude Code, Claude Desktop, Cursor, Goose, Zed) can install the server and immediately gain a full deck-management workflow.

The server has **no LLM dependency**. All cognitive work (planning, generation, verification, modification, image-card creation, OCR) runs in the host's LLM, driven by the prompts the server registers. The only required environment variable is `MOCHI_API_KEY` (and that's only needed for the Mochi-API tools — local-only workflows run with no env at all).

## 2. Goals and non-goals

**Goals**
- Become the best-in-class MCP server for Mochi: full CRUD parity with `itzcull/mochi-mcp`, plus everything that tool lacks.
- Local markdown source-of-truth, bidirectionally synced with the user's Mochi account.
- Smart workflows (`quickstart`, `generate-deck`, `extend-deck`, `modify-deck`, `review-deck`, `merge-decks`, `mirror-deck`, `delete-deck`, `browse-decks`, `make-cards-from-image`) implemented as MCP prompts the user invokes by name.
- A clear subagent architecture so individual concerns (planning, generation, verification, modification, compression, image search, structural check) are reusable across workflows.
- **Cards are simple, atomic, binary** — applies equally to text-front, image-front, image-back, and cloze cards. Non-negotiable design constraint.
- **All LLM prompts are maximally compressed.** Subagent prompts ≤ 15 lines, workflow prompts ≤ 30 lines. Role + I/O contract + hard rules. No examples, no procedural elaboration, no defensive caveats. The host LLM is trusted.
- First-class image support: Wikipedia fetch, image post-processing, user-supplied images, multimodal verification, OCR-driven card creation.
- Easy install in any MCP client.

**Non-goals (v1)**
- Hosted version. Auth or multi-user. Cloud deployment.
- Anthropic API key or any server-side LLM. The Python `deckgen` API mode and `.apkg/.csv/.zip` exporters from the previous design are deleted.
- MCP `sampling` capability (server requesting client LLM calls). Reasonable v2 addition; client support is uneven today.
- Spaced-repetition analytics workflow (retention curves, weak-card identification). Primitives are exposed; the workflow layer can be added later.
- Image generation (DALL-E / Imagen / SD). Image *acquisition* and *processing* are in v1; generating new images from scratch is not.
- PDF ingestion as a workflow. Primitives compose into it, but no dedicated v1 workflow.

## 3. Architecture overview

```
┌────────────────────────────────────────────────────────────────┐
│  mochi-tools-mcp  (Python MCP server, stdio transport)             │
│                                                                │
│  Layer 1 — Primitive tools (zero LLM)                          │
│  ┌────────────────────┐ ┌──────────────────────┐               │
│  │ Local module       │ │ Mochi API module     │               │
│  │ (file ops,         │ │ (httpx wrapper of    │               │
│  │  malformed check,  │ │  app.mochi.cards/api)│               │
│  │  image processing) │ │                      │               │
│  └──────────┬─────────┘ └──────────┬───────────┘               │
│             │          ┌───────────┘                           │
│             ▼          ▼                                       │
│  ┌────────────────────────────────┐                            │
│  │ Sync module (push/pull/status, │                            │
│  │  card-id mapping)              │                            │
│  └────────────────────────────────┘                            │
│                                                                │
│  Layer 2 — Subagent prompts (markdown files, ≤15 lines each)   │
│    DeckClarifier · DeckPlanner · CardCompressor                │
│    WebCardGenerator · ImageCardCreator · ImageSearcher         │
│    CardVerifier (multimodal-aware) · CardModifier              │
│  (CardMalformedChecker is Layer-1: regex-only, no LLM)         │
│                                                                │
│  Layer 3 — Workflow prompts (markdown files, ≤30 lines each)   │
│    quickstart · generate-deck · extend-deck · modify-deck      │
│    review-deck · merge-decks · mirror-deck · delete-deck       │
│    browse-decks · make-cards-from-image                        │
└────────────────────────────────────────────────────────────────┘
              ▲ stdio                              ▲ stdio
   ┌──────────┴───────────┐              ┌─────────┴─────────┐
   │ Claude Code          │              │ Claude Desktop /  │
   │ (parallel Agent      │              │ Cursor / Goose /  │
   │  dispatch via        │              │ Zed (serial       │
   │  .claude/agents/)    │              │  prompting)       │
   └──────────────────────┘              └───────────────────┘
```

**Constraint reminder.** MCP servers cannot run LLMs themselves. "Subagents" are prompt files the host LLM executes. In Claude Code, parallel dispatch happens via the host's native `Agent` tool, with `.claude/agents/*.md` definitions shipped in the repo. In clients without parallel dispatch, the host runs subagents serially — slower but still correct. See §15 for performance expectations per client.

## 4. Cross-cutting principles

### 4.1 Prompts are maximally compressed

The single most important design rule. Every prompt the server registers — both subagent and workflow — must contain only what the host LLM cannot infer from context.

**Hard caps:**
- Layer-2 subagent prompts: **≤ 15 lines**.
- Layer-3 workflow prompts: **≤ 30 lines**.

**Required structure (subagent):** role line · input contract · output contract · hard rules · output format.
**Required structure (workflow):** role line · numbered pipeline (one line per step) · failure-handling note if non-obvious.

**Banned:**
- Few-shot examples.
- Defensive caveats ("be sure not to..." that the LLM would already avoid).
- Procedural step-by-step descriptions inside a single step ("first do A, then B, then C" — collapse to "do A→B→C").
- "Best practices" or "tips" sections.
- Restating the global atomic-card principle (§4.2) — that's in the verifier's hard rules, not every prompt's preamble.

**Concrete example — `CardVerifier` (a Layer-2 subagent prompt, 12 lines):**

```markdown
Role: CardVerifier.

Input: one flashcard (front, back, optional image), deck topic.

Check in order:
1. Atomic — one fact only. Fail → hard.
2. Binary — back is the unique correct response to front.
3. Format — well-formed sides, no empty side, no stray separator.
4. Factual — verify claims; web_search non-obvious facts.
5. Pedagogical — clear cue on front, concise back.

Output JSON: {"verdict": "pass" | "fail", "severity": "hard" | "soft", "issues": [string]}.
```

**Concrete example — `generate-deck` (a Layer-3 workflow prompt, 16 lines):**

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
9. Parallel CardVerifier on structurally-valid cards.
10. Each fail: regen with the issue text as critique; re-verify. Cap at DECKGEN_DEFAULT_REGEN; atomicity fails bypass the cap.
11. Summary: pass / regenerated / flagged-final. For each flagged-final: [edit/accept/drop].
12. Ask: push to Mochi now? On yes → sync_push_deck. Report URL + counts.
```

These caps are enforced during code review (§16) and audited by `test_prompt_compression.py` (line-count assertion on every prompt file).

### 4.2 Cards must be simple, atomic, binary

A non-negotiable quality bar:

- **Simple** — one concept per card. No nested clauses, no list of items on the back.
- **Atomic** — tests exactly one fact, association, or relationship. Cannot be subdivided without losing meaning.
- **Binary** — the card has an unambiguous success/failure condition. A reviewer can be confidently marked right or wrong without judgment calls.

**The front does not have to be a question.** It just needs to set up a clear, unambiguous success condition. Valid front formats include:

- A question: *"What's the capital of France?"* → *"Paris"*
- An image of a thing to identify: *![flag](images/jp.png)* → *"Japan"*
- A term to define: *"Capitulate"* → *"to surrender"*
- A cloze deletion: *"The Treaty of {{c1::Westphalia}} ended the Thirty Years' War."* → *"Westphalia"*
- A translation prompt: *"el gato"* → *"the cat"*
- An expression to simplify or compute: *"$\\int_0^1 x \\, dx$"* → *"$\\frac{1}{2}$"*
- A diagram with one element highlighted, asked for by name.

What matters is that **the back is the unique correct response to the front**. Vague prompts ("explain X", "describe Y") are banned because they admit many "approximately correct" answers and corrupt the spaced-repetition signal.

The back can also be an image (e.g. "What does the Japanese flag look like?" → flag image). Atomicity applies the same way: one image, one identifiable thing.

This bar is enforced at four points:

1. **DeckPlanner** outlines: each line is one atomic fact. A request like "explain the causes of WWI" produces N separate outline lines, one per cause, not one line.
2. **WebCardGenerator / ImageCardCreator**: if a card cannot be phrased atomically, the generator returns the failure marker `CANNOT_ATOMIZE: <reason>` instead of a card. The host's workflow surfaces these to the user with the reason.
3. **CardVerifier** atomicity + binary-success check runs *before* factuality. Failures here are always regenerated, regardless of regen budget. For image cards, the verifier is invoked with the image content attached so it can confirm the image actually shows what the back claims.
4. **CardModifier** refuses transformations that would break atomicity (e.g. "combine these two cards into one").

Reference (linked in README): Andy Matuschak's *How to write good prompts*; SuperMemo's *20 rules of formulating knowledge*.

### 4.3 Local files are a staging area, not the primary mental model

Default `DECKGEN_DECKS_ROOT` is `~/.local/share/mochi-tools-mcp/decks/`, not `./decks/`. Casual users never see the filesystem; workflows phrase actions in terms of Mochi decks ("added 50 cards to *Flags* on Mochi"), not local folders. Power users override `DECKGEN_DECKS_ROOT=./decks` to hand-edit cards in their editor — that flow remains fully supported.

## 5. Repo layout (after refactor)

```
mochi-tools-mcp/
├── README.md
├── pyproject.toml                       # console script: mochi-tools-mcp
├── .gitignore
├── .env.example                         # MOCHI_API_KEY=
│
├── src/mochi_tools_mcp/
│   ├── __init__.py
│   ├── server.py                        # MCP server entry point
│   ├── config.py                        # env, decks_root resolution (XDG default)
│   ├── registry.py                      # wires tools + prompts into the server
│   ├── mochi/
│   │   ├── client.py                    # httpx wrapper of app.mochi.cards/api
│   │   ├── schemas.py                   # pydantic models for Mochi API
│   │   └── errors.py
│   ├── local/
│   │   ├── deck_fs.py                   # KEPT — card parser, deck reader
│   │   ├── image_fetch.py               # KEPT + EXTENDED — resize, format-convert, dedup
│   │   ├── image_wikipedia.py           # NEW — MediaWiki API fetcher
│   │   ├── image_import.py              # NEW — user-supplied image (path or base64)
│   │   └── malformed_check.py           # NEW — Layer-1 regex structural checker
│   ├── sync/
│   │   ├── mapping.py                   # .mochi.json read/write
│   │   ├── push.py                      # local → Mochi
│   │   ├── pull.py                      # Mochi → local
│   │   └── diff.py                      # status
│   ├── tools/
│   │   ├── local_tools.py
│   │   ├── mochi_tools.py
│   │   └── sync_tools.py
│   └── prompts/
│       ├── agents/                      # Layer-2 subagent prompts (≤15 lines each)
│       │   ├── deck_clarifier.md
│       │   ├── deck_planner.md
│       │   ├── card_compressor.md
│       │   ├── web_card_generator.md
│       │   ├── image_card_creator.md
│       │   ├── image_searcher.md        # NEW
│       │   ├── card_verifier.md
│       │   └── card_modifier.md
│       └── workflows/                   # Layer-3 workflow prompts (≤30 lines each)
│           ├── quickstart.md            # NEW
│           ├── generate_deck.md
│           ├── extend_deck.md           # renamed from add_to_deck
│           ├── modify_deck.md           # subsumes swap_sides as preset
│           ├── review_deck.md           # subsumes verify_deck via mode param
│           ├── merge_decks.md
│           ├── mirror_deck.md           # renamed from pull_deck
│           ├── delete_deck.md           # renamed from remove_deck
│           ├── browse_decks.md          # subsumes list_decks + find_card
│           └── make_cards_from_image.md # NEW
│
├── .claude/
│   └── agents/                          # Claude Code parallel subagent definitions
│       ├── deck-clarifier.md            # (frontmatter wrappers pointing to the
│       ├── deck-planner.md              #  matching file in src/mochi_tools_mcp/prompts/agents/)
│       ├── card-compressor.md
│       ├── web-card-generator.md
│       ├── image-card-creator.md
│       ├── image-searcher.md
│       ├── card-verifier.md
│       └── card-modifier.md
│
├── decks/                               # only present if user overrides DECKGEN_DECKS_ROOT
│   ├── raw/<Name>/
│   │   ├── card-NNN.md
│   │   ├── images/
│   │   ├── deck.json
│   │   └── .mochi.json                  # ID mapping after first push
│   └── .trash/                          # local soft-delete destination
│
└── tests/
    ├── fixtures/sample_deck/            # KEPT
    ├── test_parse_card.py               # KEPT
    ├── test_read_deck.py                # KEPT
    ├── test_image_fetch.py              # KEPT + EXTENDED (resize, dedup)
    ├── test_image_wikipedia.py          # NEW
    ├── test_image_import.py             # NEW
    ├── test_malformed_check.py          # NEW
    ├── test_mochi_client.py             # NEW (httpx MockTransport)
    ├── test_sync_push.py                # NEW
    ├── test_sync_pull.py                # NEW
    ├── test_sync_mapping.py             # NEW
    ├── test_server_registration.py      # NEW (all tools + prompts registered)
    └── test_prompt_compression.py       # NEW (asserts line-count caps per §4.1)
```

### 5.1 Deleted from current repo

Everything LLM-dependent or Anthropic-API-dependent. All `src/deckgen/cli.py`, `scripts/`, `src/deckgen/llm/`, `src/deckgen/pipeline/`, `src/deckgen/exporters/anki.py`, `csv_export.py`, `markdown_zip.py`, `mochi.py`, and `src/deckgen/prompts/*` and the matching tests. The `genanki`, `anthropic`, `python-dotenv`, `rich` dependencies all leave with them.

### 5.2 Kept and adapted

`deck_fs.py`, `image_fetch.py` (extended with post-processing), the sample deck fixture, and their tests. `httpx` and `pydantic` carry forward. The new MCP SDK and `Pillow` dependencies replace everything else.

## 6. Layer 1 — Primitive tools

All tools have JSON-schema input contracts (pydantic models). All return JSON. Errors return `{"isError": true, "content": [{"type": "text", "text": "..."}]}`.

### 6.1 Local tools

| Tool | Input | Output |
|---|---|---|
| `local_create_deck` | `name`, `description?`, `parent_name?` (local hierarchy) | new deck folder created |
| `local_write_card` | `deck`, `index`, `front_md`, `back_md`, `tags?`, `image_filename?` | path written |
| `local_read_card` | `deck`, `index` | card content + metadata |
| `local_list_decks` | – | array of `{name, card_count, has_mochi_mapping}` |
| `local_list_cards` | `deck` | array of `{index, front_first_line, tags, malformed?}` |
| `local_delete_card` | `deck`, `index` | moved to `decks/.trash/<deck>/<timestamp>/card-NNN.md` |
| `local_delete_deck` | `name` | folder moved to `decks/.trash/<name>-<timestamp>/` |
| `local_fetch_image` | `url`, `deck`, `max_edge_px?=1024` | downloaded filename + path; resizes, converts SVG→PNG, strips EXIF, dedups by content hash |
| `local_fetch_wikipedia_image` | `query`, `deck` | `{filename, source_url, attribution, license}` via MediaWiki API; preferred over generic web-search image URLs for factual decks |
| `local_import_image` | `deck`, `file_path?` or `base64_data?`, `filename?` | imports a user-supplied image, runs the same post-processing pipeline |
| `local_check_malformed` | `deck`, `index?` (single or whole deck) | per-card `{valid, problems[]}` — pure regex, no LLM |

Soft delete is the default. There is no hard-delete tool for local files; the user can `rm -rf <decks_root>/.trash/` to purge.

Image post-processing (applied by `local_fetch_image` and `local_import_image`): resize to max edge 1024px, convert SVG → PNG (requires optional `cairosvg`), strip EXIF, content-hash-dedup against existing images in the deck.

### 6.2 Mochi API tools (full itzcull parity)

| Tool | Mochi endpoint |
|---|---|
| `mochi_list_decks` | `GET /decks/?bookmark=...` |
| `mochi_get_deck` | `GET /decks/:id` |
| `mochi_create_deck` | `POST /decks/` |
| `mochi_update_deck` | `POST /decks/:id` |
| `mochi_delete_deck` | `DELETE /decks/:id` (hard) — see also `mochi_trash_deck` |
| `mochi_trash_deck` | `POST /decks/:id` with `trashed?: <iso>` (soft) |
| `mochi_list_cards` | `GET /cards/?deck-id=...` |
| `mochi_get_card` | `GET /cards/:id` |
| `mochi_create_card` | `POST /cards/` |
| `mochi_update_card` | `POST /cards/:id` |
| `mochi_delete_card` | `DELETE /cards/:id` (hard) |
| `mochi_trash_card` | `POST /cards/:id` with `trashed?: <iso>` |
| `mochi_add_attachment` | `POST /cards/:id/attachments/:filename` |
| `mochi_delete_attachment` | `DELETE /cards/:id/attachments/:filename` |
| `mochi_list_templates` | `GET /templates/` |
| `mochi_get_template` | `GET /templates/:id` |
| `mochi_create_template` | `POST /templates/` |
| `mochi_get_due_cards` | `GET /due` or `GET /due/:deck-id` |

Mochi's deletion endpoints are hard delete. Our `mochi_trash_*` wrappers are convenience aliases over `update` with `trashed?`. Workflows default to trash; users get hard-delete only by calling the primitive directly.

Auth: HTTP Basic with `MOCHI_API_KEY` as username, empty password. Per-request retry with backoff on 429 and 5xx (max 5 attempts).

### 6.3 Sync tools

| Tool | Behavior |
|---|---|
| `sync_push_deck` | Reads `<decks_root>/raw/<name>/`. If `.mochi.json` exists, updates existing deck/cards by ID (only those whose `content_hash` changed). Otherwise creates a new Mochi deck, all cards, all attachments, writes `.mochi.json`. Returns Mochi deck URL + per-card create/update counts. |
| `sync_pull_deck` | Reads remote deck + cards by `mochi_deck_id`. Writes `card-NNN.md` files locally, rewriting `@media/<x>` references to `images/<x>` (but doesn't download binaries — Mochi API doesn't expose download; see §14 open question). Writes `attachments-not-downloaded.txt` listing each unfetchable filename and warns. Writes `.mochi.json` mapping. |
| `sync_status` | Compares local and remote, returns per-card status: `new-locally`, `changed-locally`, `new-remotely`, `changed-remotely`, `in-sync`. |
| `sync_link` | Associates an existing local folder with an existing Mochi deck ID. Writes `.mochi.json` with ID + zero-hash entries. Next `sync_push_deck` performs a full update sweep. |

#### 6.3.1 `.mochi.json` mapping format

```json
{
  "deck_id": "abc123",
  "deck_name_on_mochi": "Flags",
  "parent_id": "JOJQQGmL",
  "template_id": null,
  "cards": {
    "card-001.md": {
      "id": "card_xyz",
      "content_hash": "sha1:abcdef..."
    }
  },
  "images": {
    "images/jp.png": "sha1:..."
  },
  "last_push_at": "2026-05-10T20:00:00Z"
}
```

`content_hash` enables fast incremental push. `images` map ditto for attachments — `sync_push_deck` skips re-upload of images whose hash matches.

## 7. Layer 2 — Subagent prompts

Each lives at `src/mochi_tools_mcp/prompts/agents/<name>.md`. Each is also surfaced as an MCP prompt AND an MCP resource so users can `@mention` and read them in clients that support resources. Each has a matching `.claude/agents/<name>.md` frontmatter file pointing to the same content for Claude Code parallel dispatch.

**Each prompt is ≤ 15 lines and begins with `Role: <name>.`** See §4.1 for the structure and a worked example.

| Subagent | Purpose | Tools required | Output format |
|---|---|---|---|
| **DeckClarifier** | Given topic+size+target Mochi parent deck, produce 2–4 follow-up questions. Skip anything implied. | – | JSON `{questions: [{id, question, type, options?}]}` |
| **DeckPlanner** | Given topic+size+answers (+ optional existing-card summaries), produce N outline lines, each atomic. | – | text, `NNN. <atomic prompt> → <atomic answer hint>` per line |
| **CardCompressor** | Compress a card into a one-line summary for dedup or planner context. | – | one line of text |
| **WebCardGenerator** | One outline line → one card. May call `web_search` for facts. Surface `CANNOT_ATOMIZE: <reason>` on failure. | `web_search` | markdown card or failure marker |
| **ImageCardCreator** | Concept + side (front \| back) → one card with image on the chosen side, atomic fact on the other. Resolves the image via ImageSearcher or a supplied URL. | – | markdown card or failure marker |
| **ImageSearcher** | Concept → N candidate image URLs with thumbnails, descriptions, sources. Prefers Wikipedia via `local_fetch_wikipedia_image`. | `web_search`, `local_fetch_wikipedia_image` | JSON `[{url, thumbnail, description, source, license}]` |
| **CardVerifier** | Multimodal-aware. Check atomicity → binary → format → factuality → pedagogy. For image cards, the image content is attached so the verifier sees what the back claims. | `web_search` | JSON `{verdict, severity, issues}` |
| **CardModifier** | Apply a described transformation. Refuse if it would break atomicity. | – | modified markdown card |

CardMalformedChecker is **not** in Layer 2 — it's a pure regex tool in Layer 1.

## 8. Layer 3 — Workflows

10 named workflows. Each is an MCP prompt the user invokes by name. Below is the user-visible pipeline for each. Subagent dispatch happens in parallel where the host LLM supports it, otherwise serially (see §15).

### 8.1 `quickstart`

The first-run entry point. Ping `mochi_list_decks` to validate auth; if missing/invalid, print the exact URL (`https://app.mochi.cards/` → avatar → Account Settings → API Keys) and exit. On success, show existing Mochi decks + card counts, then offer: *create a new deck* / *extend an existing deck* / *modify an existing deck* / *mirror a deck for local editing* / *make cards from an image*. Hands off to the chosen workflow.

### 8.2 `generate-deck`

1. Ask: deck description.
2. Ask: size (default 50).
3. Call `mochi_list_decks`; show; ask parent deck (optional).
4. Call `mochi_list_templates`; ask template (or none).
5. Dispatch DeckClarifier → ask the user the returned questions.
6. Dispatch DeckPlanner → outline. Show; accept approve/edit/regenerate.
7. Parallel WebCardGenerator per outline line → `local_write_card`. Surface any `CANNOT_ATOMIZE`.
8. `local_check_malformed` across all cards; queue malformed for regen.
9. Parallel CardVerifier on structurally-valid cards (image cards include their image content).
10. Each fail: regen with the issue text as critique; re-verify. Cap at `DECKGEN_DEFAULT_REGEN`; atomicity fails bypass the cap.
11. Summary: pass / regenerated / flagged-final. For each flagged-final: `[edit / accept / drop]`.
12. Ask: push to Mochi now? On yes → `sync_push_deck`. Report URL + counts.

### 8.3 `extend-deck` (was `add-to-deck`)

1. Ask: which deck?
2. `local_list_cards` + parallel CardCompressor over existing cards → dedup context.
3. Ask: what to add? (free text, count).
4. DeckPlanner with existing-card summaries in context → new outline that avoids duplicates.
5. Approve outline.
6. Generate / verify / regen pipeline identical to `generate-deck` steps 7–11.
7. Append (new index = max existing + 1, …).
8. Push to Mochi (uses `sync_push_deck` incremental mode).

### 8.4 `modify-deck`

Subsumes the previous `swap-sides` workflow as a preset.

1. Ask: which deck? what transformation? (Presets: `swap-sides`, `to-cloze`, `make-harder`, `add-tags`. Or freeform.)
2. `local_list_cards` → ask scope (all / by tag / by content match).
3. Sample 3 representative cards in scope.
4. Dispatch 3 × CardModifier on samples → show before/after diff.
5. User: approve / adjust wording / abort. For global presets like `swap-sides`, require an extra confirmation since the operation is destructive across all cards.
6. On approve: dispatch CardModifier on full scope in parallel.
7. Dispatch CardVerifier on modified cards. Atomicity-fail → revert that card and warn.
8. Show flagged cards for review.
9. Push to Mochi (incremental update).

### 8.5 `review-deck`

Subsumes the previous `verify-deck` workflow via a `mode` parameter.

1. Ask: which deck? `mode` = `auto` (verify+flag, batch fixes) or `manual` (per-card walkthrough).
2. Run `local_check_malformed` → list structural failures.
3. **`auto`**: dispatch CardVerifier in parallel on structurally-valid cards; categorize by severity; for each non-pass card show issue, offer `[edit / regen / accept / skip]`.
4. **`manual`**: iterate cards; for each, display front+back, ask `[keep / edit / regenerate / delete / skip]`.
5. Apply actions (CardModifier for "edit with description", WebCardGenerator for "regen").
6. Re-verify the modified subset.
7. Push updates.

### 8.6 `merge-decks`

1. Ask: deck A, deck B, target name, drop duplicates? parent on Mochi?
2. Parallel CardCompressor on all cards in both decks.
3. Identify duplicates by compressed summary similarity. Show conflicts to user (which copy to keep, or merge content).
4. Write merged deck locally.
5. Push to Mochi as new deck.
6. Ask: trash the originals?

### 8.7 `mirror-deck` (was `pull-deck`)

1. Open with the disclosure: "Mochi's API does not expose attachment downloads. This mirror preserves image *references* but not the binaries themselves. Continue?"
2. `mochi_list_decks` → numbered list. User picks a deck (by index or name).
3. `mochi_list_cards(deck_id)` with pagination.
4. For each card: parse content into front/back, write `card-NNN.md`. Rewrite `@media/<x>` references to `images/<x>`.
5. Write `.mochi.json` mapping.
6. Write `attachments-not-downloaded.txt` listing missing binaries.

If the §14 spike on the undocumented Mochi attachment-download endpoint succeeds, this workflow becomes a true round-trip and the disclosure is dropped.

### 8.8 `delete-deck` (was `remove-deck`)

1. Ask: which deck?
2. Show stats: card count, last push, in-Mochi-or-local-only.
3. Ask: trash (default) or hard-delete? (Hard requires typing "DELETE" to confirm.)
4. On trash: `mochi_trash_deck` + `local_delete_deck` (both soft).
5. On hard: `mochi_delete_deck` + remove local folder (`local_delete_deck` still soft-moves locally; the user can purge `.trash/` manually).
6. Report.

### 8.9 `browse-decks` (was `list-decks` + `find-card`)

1. `mochi_list_decks` + `local_list_decks` in parallel. Merge via deck IDs in `.mochi.json` mappings.
2. Show a table: name | source (local / mochi / both) | card count | last push | parent.
3. Optional: user supplies a free-text query → grep local files + paginate Mochi cards substring-matched. Show results with card IDs and source paths.

### 8.10 `make-cards-from-image` (NEW)

Requires a multimodal host LLM. User-supplied image (path, base64, or pasted into the chat).

1. Ask: target deck? (existing or new).
2. Accept image via `local_import_image`.
3. Host LLM OCRs / interprets the image (textbook page, slide, diagram, screenshot of a list).
4. Dispatch DeckPlanner with the extracted content → atomic outline.
5. Approve outline.
6. Parallel WebCardGenerator (and/or ImageCardCreator if the image itself or sub-crops belong on a card) → cards.
7. Verify / regen pipeline identical to `generate-deck` steps 8–11.
8. Push to Mochi.

## 9. Install + integration

The server is distributed as a Python package with a console-script entry point `mochi-tools-mcp`.

### 9.1 Install

```bash
pip install git+https://github.com/oh54321/mochi-tools-mcp.git
# or with uv:
uv tool install git+https://github.com/oh54321/mochi-tools-mcp.git
# or from clone:
git clone … && cd … && pip install -e .
```

Optional extras: `pip install 'mochi-tools-mcp[svg]'` enables SVG → PNG conversion via `cairosvg` (for Wikipedia flag SVGs, etc.).

### 9.2 Wire up — Claude Code (headline two-liner)

```bash
claude mcp add deckgen --env MOCHI_API_KEY=mochi_xxx -- mochi-tools-mcp
ln -s "$(mochi-tools-mcp --agents-path)" ~/.claude/agents/deckgen
```

Line 1 registers the server. Line 2 enables parallel subagent dispatch. Skip line 2 and workflows still run, just serially.

### 9.3 Wire up — Claude Desktop / Cursor / Goose / Zed

```json
{
  "mcpServers": {
    "deckgen": {
      "command": "mochi-tools-mcp",
      "env": {"MOCHI_API_KEY": "mochi_xxx"}
    }
  }
}
```

### 9.4 Environment

| Var | Required? | Default | Effect |
|---|---|---|---|
| `MOCHI_API_KEY` | For `mochi_*` and `sync_*` tools | – | HTTP Basic auth username |
| `DECKGEN_DECKS_ROOT` | Optional | `~/.local/share/mochi-tools-mcp/decks/` | Where local decks live. Override to `./decks` for hand-editing |
| `DECKGEN_DEFAULT_REGEN` | Optional | `1` | Max regen attempts in workflows |
| `DECKGEN_DEFAULT_CONCURRENCY` | Optional | `10` | Hint to workflows for parallel dispatch batch size |

## 10. Error handling

Boundaries only:

- Missing `MOCHI_API_KEY` → `mochi_*` and `sync_*` tools return: *"MOCHI_API_KEY missing. Get a key at https://app.mochi.cards/ → click your avatar → Account Settings → API Keys, then set `MOCHI_API_KEY=<key>` in your MCP client config."*
- Mochi 429 / 5xx → exponential backoff + jitter, 5 retries.
- Mochi 401 → flag as auth error, do not retry; same URL hint as above.
- Mochi 404 on a known mapped card ID → mark stale in `.mochi.json` and surface to user; next push will treat as new.
- Image fetch failure during `local_fetch_image` → warn, return null, workflow continues.
- SVG conversion failure (cairosvg not installed) → warn, save the raw SVG, suggest `pip install 'mochi-tools-mcp[svg]'`.
- Local file conflicts (existing `<decks_root>/raw/<Name>/` on `generate-deck`) → refuse; suggest `extend-deck` or different name. No `--overwrite` flag; users delete the folder themselves.
- `CANNOT_ATOMIZE` from generators → surface to user with the reason. Never silently dropped.

## 11. Testing

- `test_parse_card.py`, `test_read_deck.py` — kept from previous repo.
- `test_image_fetch.py` — extended: resize, EXIF strip, SVG→PNG path, content-hash dedup.
- `test_image_wikipedia.py` — NEW. `httpx.MockTransport` against MediaWiki API.
- `test_image_import.py` — NEW. File path and base64 inputs.
- `test_malformed_check.py` — pure regex, exhaustive cases.
- `test_mochi_client.py` — `httpx.MockTransport`, full CRUD paths plus 429 retry behavior.
- `test_sync_mapping.py` — round-trip `.mochi.json`.
- `test_sync_push.py` — fake Mochi client; verify incremental push skips unchanged hashes, creates new cards, updates changed cards.
- `test_sync_pull.py` — fake Mochi client returning canned cards; verify markdown files written with correct image-ref rewriting and `attachments-not-downloaded.txt`.
- `test_server_registration.py` — start the MCP server in-process, query `tools/list` and `prompts/list`, assert every Layer-1 tool and Layer-3 workflow prompt is registered with a valid schema.
- `test_prompt_compression.py` — NEW. Asserts every file in `src/mochi_tools_mcp/prompts/agents/` has ≤15 non-blank lines and every file in `src/mochi_tools_mcp/prompts/workflows/` has ≤30 non-blank lines. Fails the build if a prompt grows past the cap.

No live LLM tests; subagent prompts are static markdown. The README documents how to manually exercise each workflow against a real Mochi account (§16 manual integration test).

## 12. Comparison vs. itzcull/mochi-mcp

| Capability | itzcull | This server |
|---|---|---|
| Mochi CRUD (cards, decks, templates, attachments, due) | ✓ | ✓ (full parity) |
| Local markdown source-of-truth | ✗ | ✓ |
| Bidirectional sync with ID mapping | ✗ | ✓ |
| Subagent prompts (planner, generator, verifier, modifier, compressor, image-searcher) | ✗ | ✓ |
| Workflow prompts (10 named workflows) | ✗ | ✓ |
| Atomic-card quality gate | ✗ | ✓ (CardVerifier + planner + generator) |
| Soft-delete by default | ✗ (hard delete) | ✓ |
| Incremental push via content hashes | ✗ | ✓ |
| Hierarchy / parent-id support | partial | ✓ |
| Cloze, image cards, template-aware generation | ✗ | ✓ |
| Image post-processing (resize, format, dedup) | ✗ | ✓ |
| Wikipedia / curated image source | ✗ | ✓ |
| Vision-aware verification of image cards | ✗ | ✓ |
| Make cards from user-supplied images / OCR | ✗ | ✓ |
| No server-side LLM dependency | ✓ | ✓ |

## 13. Dependencies

Runtime: `mcp`, `httpx`, `pydantic`, `Pillow`. Optional extra `[svg]`: `cairosvg`. (Removed from previous design: `anthropic`, `genanki`, `python-dotenv`, `rich`.)

Dev: `pytest`, `pytest-asyncio`, `ruff`, `mypy`.

## 14. Open questions for implementation

- Confirm the exact MCP Python SDK package name and minimum version when implementation starts (`mcp` is the canonical name as of late 2025; verify current API).
- Confirm Mochi's `parent-id` semantics for top-level decks (empty string vs. omit vs. null).
- Decide whether `sync_pull_deck` should write a placeholder zero-byte file for missing attachments or leave the path absent. (Current spec leaves absent.)
- Subagent prompt files: pick a canonical model in the README for "what model are these tuned against" — the user's Claude Code default (Sonnet 4.6) is the reference target.
- **Mochi attachment-download spike (30 min):** the Mochi web app must fetch attachments to render cards; an undocumented `GET /cards/:id/attachments/:filename` (or similar) using the same Basic auth is plausible. If it works, expose as `mochi_download_attachment` and drop the `mirror-deck` disclosure + `attachments-not-downloaded.txt` warning.

## 15. Performance characteristics

Honest expectations so users pick the right client:

| Client | 50-card generate | 50-card verify | Notes |
|---|---|---|---|
| Claude Code (parallel `Agent` dispatch) | ~30–60s | ~30–60s | True parallelism via `.claude/agents/` |
| Claude Desktop / Cursor / Goose / Zed (serial) | ~5–10min | ~5–10min | Each subagent dispatch is a separate LLM turn |

Recommend Claude Code in the README for any deck > 20 cards. The non-parallel experience is correct but slow.

## 16. Implementation quality gate

The refactor is **not complete** until all of the following pass and are recorded as the final task in the implementation plan:

- `pytest` — all tests pass.
- Code coverage on `src/mochi_tools_mcp/local/`, `mochi/`, `sync/`, `tools/` ≥ 90%.
- `ruff check .` — zero warnings.
- `ruff format --check .` — formatted.
- `mypy src/mochi_tools_mcp/` — clean under strict mode (`--strict`).
- `test_prompt_compression.py` — every prompt within its line cap (§4.1).
- `test_server_registration.py` — every Layer-1 tool and Layer-3 workflow prompt is registered with a valid input schema.
- **Manual integration test** (documented checklist in README): one full run of each workflow against a sandbox Mochi account, with screenshots of (a) generated cards in Mochi, (b) `mirror-deck` round-trip, (c) `modify-deck` swap-sides preset.

Verification is a single make target / script: `./scripts/verify.sh` runs all automated checks above and prints a green/red summary. The implementation plan's last task runs this script and pastes the output; "all green" is the merge criterion.

No "looks good to me" claims without evidence from this gate.
