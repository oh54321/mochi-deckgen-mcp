import json
from pathlib import Path

from deckgen.llm.client import LLMRequest
from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.orchestrator import GenerationInputs, run_pipeline


async def test_full_pipeline_writes_raw_and_exports(tmp_path):
    def responder(req: LLMRequest) -> str:
        s = req.system
        if "planner" in s:
            return "\n".join(f"{i:03d}. card {i} → ans" for i in range(1, 4))
        if "researcher" in s:
            return json.dumps({"cards": [{"index": i, "facts": [f"fact {i}"], "image_url": None} for i in range(1, 4)]})
        if "verifier" in s:
            return '{"verdict":"pass","severity":"low","issues":[]}'
        return "Q\n\n---\n\nA\n"
    fake = FakeLLMClient(responder=responder)

    inputs = GenerationInputs(
        name="Sample",
        topic="Sample topic",
        description="A sample deck",
        size=3,
        formats=["mochi", "csv"],
        follow_ups={},
    )
    result = await run_pipeline(
        client=fake, inputs=inputs,
        decks_raw=tmp_path / "raw", decks_exported=tmp_path / "exported",
        concurrency=2, regen=1,
    )
    raw_dir = tmp_path / "raw" / "Sample"
    assert (raw_dir / "deck.json").exists()
    assert len(list(raw_dir.glob("card-*.md"))) == 3
    exports = list((tmp_path / "exported" / "Sample").iterdir())
    suffixes = {p.suffix for p in exports}
    assert suffixes == {".mochi", ".csv"}
    assert result.report and all(r.final_verdict == "pass" for r in result.report)
