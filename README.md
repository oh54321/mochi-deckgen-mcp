# deckgen-mcp

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
pip install git+https://github.com/oh54321/spaced-repetition-deck-generation.git
# Optional: enable SVG → PNG conversion (Wikipedia flag SVGs etc.)
pip install 'deckgen-mcp[svg]'
```

You'll need a Mochi API key. Get one at https://app.mochi.cards/ → click your avatar → Account Settings → API Keys.

## Wire up

### Claude Code (recommended)

```bash
claude mcp add deckgen --env MOCHI_API_KEY=mochi_xxx -- deckgen-mcp
ln -s "$(deckgen-mcp --agents-path)" ~/.claude/agents/deckgen
```

Line 2 enables parallel subagent dispatch. Skip it and workflows still run, just serially.

### Claude Desktop / Cursor / Goose / Zed

Add to your MCP config:

```json
{
  "mcpServers": {
    "deckgen": {
      "command": "deckgen-mcp",
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
| `DECKGEN_DECKS_ROOT` | optional | `~/.local/share/deckgen-mcp/decks/` | Override to `./decks` to hand-edit cards |
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
