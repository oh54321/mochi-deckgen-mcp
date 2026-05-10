from deckgen.llm.client import LLMRequest
from deckgen.llm.fake_client import FakeLLMClient


async def test_fake_dict_routing():
    fake = FakeLLMClient(responder={"planner": "outline\n", "verifier": '{"verdict":"pass"}'})
    r1 = await fake.complete(LLMRequest(system="you are the planner", user="x"))
    r2 = await fake.complete(LLMRequest(system="you are the verifier", user="y"))
    assert r1.text == "outline\n"
    assert r2.text.startswith("{")
    assert len(fake.calls) == 2
