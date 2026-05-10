import json

from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.plan import OutlineCard
from deckgen.pipeline.research import research_outline


async def test_research_attaches_facts_and_images():
    payload = {
        "cards": [
            {"index": 1, "facts": ["red disc on white"], "image_url": "https://example.com/jp.png"},
            {"index": 2, "facts": ["tricolour"], "image_url": None},
        ]
    }
    fake = FakeLLMClient(responder=lambda req: json.dumps(payload))
    outline = [OutlineCard(1, "Japan → name"), OutlineCard(2, "France → name")]
    res = await research_outline(fake, outline=outline, topic="Flags")
    assert res[1].facts == ["red disc on white"]
    assert res[1].image_url == "https://example.com/jp.png"
    assert res[2].image_url is None
