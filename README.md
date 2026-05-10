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
