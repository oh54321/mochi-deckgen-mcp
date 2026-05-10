from deckgen.llm.client import LLMRequest
from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.generate import _filename
from deckgen.pipeline.plan import OutlineCard
from deckgen.pipeline.research import ResearchedCard
from deckgen.pipeline.verify import verify_cards


async def test_verify_passes_through_when_all_pass(tmp_path):
    out_dir = tmp_path
    for i in (1, 2):
        (out_dir / _filename(i, 2)).write_text("Q\n---\nA\n", encoding="utf-8")
    fake = FakeLLMClient(responder=lambda req: '{"verdict":"pass","severity":"low","issues":[]}')
    outline = [OutlineCard(1, "a"), OutlineCard(2, "b")]
    researched = {c.index: ResearchedCard(outline=c) for c in outline}
    report = await verify_cards(
        fake, generator=fake, outline=outline, researched=researched, follow_ups={},
        out_dir=out_dir, concurrency=2, regen=1,
    )
    assert all(r.final_verdict == "pass" for r in report)


async def test_verify_triggers_regen_then_keeps_last(tmp_path):
    out_dir = tmp_path
    (out_dir / _filename(1, 1)).write_text("bad\n---\nbad\n", encoding="utf-8")
    outline = [OutlineCard(1, "x")]
    researched = {1: ResearchedCard(outline=outline[0])}

    verifier_responses = iter([
        '{"verdict":"fail","severity":"high","issues":["wrong"]}',
        '{"verdict":"pass","severity":"low","issues":[]}',
    ])

    def vresponder(req: LLMRequest) -> str:
        if "verifier" in req.system:
            return next(verifier_responses)
        # generator response (regen)
        return "fixed\n---\nfixed\n"

    fake = FakeLLMClient(responder=vresponder)
    report = await verify_cards(
        fake, generator=fake, outline=outline, researched=researched, follow_ups={},
        out_dir=out_dir, concurrency=1, regen=1,
    )
    assert report[0].final_verdict == "pass"
    assert "fixed" in (out_dir / _filename(1, 1)).read_text()
