from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMRequest:
    system: str
    user: str
    tools: list[str] = field(default_factory=list)  # e.g. ["web_search"]
    max_tokens: int = 2048
    temperature: float = 0.5


@dataclass
class LLMResponse:
    text: str
    raw: object = None


class LLMClient(Protocol):
    async def complete(self, req: LLMRequest) -> LLMResponse: ...
