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
