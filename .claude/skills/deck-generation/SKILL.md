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

Run `python scripts/export_only.py --name <Name> --format <fmt>` (repeat `--format` for multiple) to produce export files.

Report the final paths to the user.

## Rules

- Refuse to overwrite an existing `decks/raw/<Name>/`. Ask the user to choose a new name or pass overwrite intent.
- Never invent facts; rely on the research stage.
- Keep your own messages terse. Show progress concisely.
