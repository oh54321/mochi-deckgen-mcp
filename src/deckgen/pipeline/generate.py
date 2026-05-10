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
