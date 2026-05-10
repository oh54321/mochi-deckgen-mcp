from __future__ import annotations

import argparse
import asyncio
import sys

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
