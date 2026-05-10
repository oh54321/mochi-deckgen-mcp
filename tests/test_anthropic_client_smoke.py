import os

import pytest

from deckgen.config import Config
from deckgen.llm.anthropic_client import AnthropicClient
from deckgen.llm.client import LLMRequest


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="no API key")
async def test_smoke_complete():
    client = AnthropicClient(Config.from_env())
    resp = await client.complete(LLMRequest(system="reply with the single word PONG", user="ping", max_tokens=20))
    assert "PONG" in resp.text.upper()
