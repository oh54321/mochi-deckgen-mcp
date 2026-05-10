from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from deckgen.llm.client import LLMRequest, LLMResponse


@dataclass
class FakeLLMClient:
    """Deterministic LLM stand-in for tests.

    Pass a callable that maps an LLMRequest to a string response,
    or a dict keyed on a substring of the system prompt.
    """
    responder: Callable[[LLMRequest], str] | dict[str, str] | None = None
    calls: list[LLMRequest] = field(default_factory=list)

    async def complete(self, req: LLMRequest) -> LLMResponse:
        self.calls.append(req)
        if callable(self.responder):
            return LLMResponse(text=self.responder(req))
        if isinstance(self.responder, dict):
            for key, val in self.responder.items():
                if key in req.system:
                    return LLMResponse(text=val)
        return LLMResponse(text="")
