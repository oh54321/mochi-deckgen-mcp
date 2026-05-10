from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field
from pathlib import Path

from deckgen.io.deck_fs import read_deck
from deckgen.io.image_fetch import fetch_image
from deckgen.llm.client import LLMClient
from deckgen.pipeline.export import export_deck
from deckgen.pipeline.generate import generate_cards
from deckgen.pipeline.plan import generate_outline
from deckgen.pipeline.research import research_outline
from deckgen.pipeline.verify import CardReport, verify_cards


@dataclass
class GenerationInputs:
    name: str
    topic: str
    description: str
    size: int
    formats: list[str]
    follow_ups: dict[str, str] = field(default_factory=dict)


@dataclass
class GenerationResult:
    raw_folder: Path
    exports: list[Path]
    report: list[CardReport]


def _write_deck_json(folder: Path, inputs: GenerationInputs) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "deck.json").write_text(json.dumps({
        "name": inputs.name,
        "description": inputs.description,
        "created_at": _dt.datetime.now(_dt.UTC).isoformat().replace("+00:00", "Z"),
        "generator_version": "0.1.0",
        "source_topic": inputs.topic,
        "follow_up_answers": inputs.follow_ups,
    }, indent=2), encoding="utf-8")


async def run_pipeline(
    *,
    client: LLMClient,
    inputs: GenerationInputs,
    decks_raw: Path,
    decks_exported: Path,
    concurrency: int,
    regen: int,
    overwrite: bool = False,
    append: bool = False,
) -> GenerationResult:
    raw_folder = Path(decks_raw) / inputs.name
    if raw_folder.exists() and not (overwrite or append):
        raise FileExistsError(
            f"{raw_folder} already exists. Use --overwrite to replace or --append to add cards."
        )
    if overwrite and raw_folder.exists():
        import shutil
        shutil.rmtree(raw_folder)
    _write_deck_json(raw_folder, inputs)

    outline = await generate_outline(client, topic=inputs.topic, size=inputs.size, follow_ups=inputs.follow_ups)
    researched = await research_outline(client, outline=outline, topic=inputs.topic)

    images_dir = raw_folder / "images"
    image_filenames: dict[int, str] = {}
    for idx, rc in researched.items():
        if rc.image_url:
            p = fetch_image(rc.image_url, images_dir)
            if p is not None:
                image_filenames[idx] = p.name

    await generate_cards(
        client, outline=outline, researched=researched, follow_ups=inputs.follow_ups,
        out_dir=raw_folder, concurrency=concurrency, image_filenames=image_filenames,
    )
    report = await verify_cards(
        client, generator=client, outline=outline, researched=researched, follow_ups=inputs.follow_ups,
        out_dir=raw_folder, concurrency=concurrency, regen=regen, image_filenames=image_filenames,
    )

    deck = read_deck(raw_folder)
    exports = export_deck(deck, out_root=Path(decks_exported), formats=inputs.formats)
    return GenerationResult(raw_folder=raw_folder, exports=exports, report=report)
