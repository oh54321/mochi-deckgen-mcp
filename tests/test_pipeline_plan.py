from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.plan import generate_outline


async def test_generate_outline_returns_one_line_per_card():
    fake = FakeLLMClient(responder=lambda req: "\n".join(
        [f"{i:03d}. card {i} → ans" for i in range(1, 6)]
    ))
    outline = await generate_outline(fake, topic="X", size=5, follow_ups={})
    assert len(outline) == 5
    assert outline[0].index == 1
    assert outline[4].hint_text.startswith("card 5")
