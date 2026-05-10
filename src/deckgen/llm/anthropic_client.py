from __future__ import annotations

import asyncio
import logging
import random

from anthropic import AsyncAnthropic, APIStatusError, RateLimitError

from deckgen.config import Config
from deckgen.llm.client import LLMRequest, LLMResponse

log = logging.getLogger(__name__)


class AnthropicClient:
    def __init__(self, config: Config):
        if not config.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set; copy .env.example to .env")
        self._client = AsyncAnthropic(api_key=config.api_key)
        self._model = config.model

    async def complete(self, req: LLMRequest) -> LLMResponse:
        tools = []
        if "web_search" in req.tools:
            tools.append({"type": "web_search_20250828", "name": "web_search"})

        for attempt in range(5):
            try:
                resp = await self._client.messages.create(
                    model=self._model,
                    system=req.system,
                    max_tokens=req.max_tokens,
                    temperature=req.temperature,
                    tools=tools or None,
                    messages=[{"role": "user", "content": req.user}],
                )
                text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
                return LLMResponse(text=text, raw=resp)
            except (RateLimitError, APIStatusError) as e:
                if attempt == 4:
                    raise
                delay = (2 ** attempt) + random.uniform(0, 1)
                log.warning("LLM retry %d/5 after %s: %.1fs", attempt + 1, type(e).__name__, delay)
                await asyncio.sleep(delay)
        raise RuntimeError("unreachable")
