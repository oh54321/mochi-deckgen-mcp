from deckgen.llm.fake_client import FakeLLMClient
from deckgen.pipeline.generate import generate_cards
from deckgen.pipeline.plan import OutlineCard
from deckgen.pipeline.research import ResearchedCard


async def test_generate_writes_one_md_per_card(tmp_path):
    def responder(req):
        return "Q?\n\n---\n\nA"
    fake = FakeLLMClient(responder=responder)

    outline = [OutlineCard(i, f"item {i}") for i in (1, 2, 3)]
    researched = {c.index: ResearchedCard(outline=c) for c in outline}
    out_dir = tmp_path / "cards"
    written = await generate_cards(
        fake, outline=outline, researched=researched, follow_ups={}, out_dir=out_dir, concurrency=3,
    )
    assert len(written) == 3
    assert (out_dir / "card-001.md").read_text().startswith("Q?")
    assert (out_dir / "card-003.md").exists()
