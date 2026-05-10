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
    out: dict[int, ResearchedCard] = {}
    for c in outline:
        out[c.index] = ResearchedCard(outline=c)
    for item in data.get("cards", []):
        idx = item["index"]
        if idx in out:
            out[idx].facts = item.get("facts", [])
            out[idx].image_url = item.get("image_url")
    return out
