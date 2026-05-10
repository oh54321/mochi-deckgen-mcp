from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from deckgen.config import PROMPTS_DIR
from deckgen.llm.client import LLMClient, LLMRequest


@dataclass
class FollowUp:
    id: str
    question: str
    type: str
    options: list[str] | None = None


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


async def generate_follow_ups(
    client: LLMClient, *, topic: str, size: int, formats: list[str]
) -> list[FollowUp]:
    user = json.dumps({"topic": topic, "size": size, "formats": formats})
    resp = await client.complete(LLMRequest(system=_load_prompt("clarifier"), user=user, max_tokens=1024, temperature=0.3))
    data = json.loads(resp.text)
    return [
        FollowUp(id=q["id"], question=q["question"], type=q["type"], options=q.get("options"))
        for q in data["questions"]
    ]
