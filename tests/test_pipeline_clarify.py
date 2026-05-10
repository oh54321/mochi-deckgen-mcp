import json

from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.clarify import generate_follow_ups


async def test_generate_follow_ups_parses_json():
    payload = {
        "questions": [
            {"id": "scope", "question": "UN only?", "type": "choice", "options": ["yes", "no"]},
            {"id": "back", "question": "Country name on back?", "type": "free"},
        ]
    }
    fake = FakeLLMClient(responder=lambda req: json.dumps(payload))
    qs = await generate_follow_ups(fake, topic="Flags of Africa", size=60, formats=["mochi"])
    assert len(qs) == 2
    assert qs[0].id == "scope"
    assert qs[0].options == ["yes", "no"]
