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
