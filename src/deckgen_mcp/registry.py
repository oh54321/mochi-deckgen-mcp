from __future__ import annotations

from pathlib import Path

from deckgen_mcp.tools import local_tools, mochi_tools, sync_tools

PROMPTS_DIR = Path(__file__).parent / "prompts"
AGENTS_DIR = PROMPTS_DIR / "agents"
WORKFLOWS_DIR = PROMPTS_DIR / "workflows"


def all_tools() -> list[dict]:
    return [*local_tools.collect(), *mochi_tools.collect(), *sync_tools.collect()]


def _slug(p: Path) -> str:
    return p.stem.replace("_", "-")


def all_prompts() -> list[dict]:
    prompts: list[dict] = []
    for p in sorted(AGENTS_DIR.glob("*.md")):
        prompts.append({"name": _slug(p), "path": p, "kind": "agent",
                        "description": f"Subagent: {_slug(p)}"})
    for p in sorted(WORKFLOWS_DIR.glob("*.md")):
        prompts.append({"name": _slug(p), "path": p, "kind": "workflow",
                        "description": f"Workflow: {_slug(p)}"})
    return prompts


def all_resources() -> list[dict]:
    resources: list[dict] = []
    for p in sorted(AGENTS_DIR.glob("*.md")):
        resources.append({
            "uri": f"deckgen://prompts/agents/{_slug(p)}",
            "name": _slug(p),
            "mimeType": "text/markdown",
            "path": p,
        })
    return resources
