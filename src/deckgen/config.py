from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_CONCURRENCY = 10
DEFAULT_REGEN = 1
DEFAULT_SIZE = 50
DEFAULT_FORMATS = ("mochi",)

REPO_ROOT = Path(__file__).resolve().parents[2]
DECKS_RAW = REPO_ROOT / "decks" / "raw"
DECKS_EXPORTED = REPO_ROOT / "decks" / "exported"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


@dataclass
class Config:
    api_key: str | None
    model: str = DEFAULT_MODEL
    concurrency: int = DEFAULT_CONCURRENCY
    regen: int = DEFAULT_REGEN

    @classmethod
    def from_env(cls) -> "Config":
        return cls(api_key=os.environ.get("ANTHROPIC_API_KEY"))
