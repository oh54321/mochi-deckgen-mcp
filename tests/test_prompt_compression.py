from pathlib import Path

ROOT = Path(__file__).parent.parent / "src" / "deckgen_mcp" / "prompts"
AGENTS = ROOT / "agents"
WORKFLOWS = ROOT / "workflows"

AGENT_MAX = 15
WORKFLOW_MAX = 30


def _non_blank_lines(path: Path) -> int:
    return sum(1 for line in path.read_text().splitlines() if line.strip())


def test_agent_prompts_under_cap():
    files = list(AGENTS.glob("*.md"))
    assert files, "No agent prompts found"
    for f in files:
        n = _non_blank_lines(f)
        assert n <= AGENT_MAX, f"{f.name}: {n} non-blank lines > {AGENT_MAX}"


def test_workflow_prompts_under_cap():
    files = list(WORKFLOWS.glob("*.md"))
    assert files, "No workflow prompts found"
    for f in files:
        n = _non_blank_lines(f)
        assert n <= WORKFLOW_MAX, f"{f.name}: {n} non-blank lines > {WORKFLOW_MAX}"


def test_agent_prompts_start_with_role_line():
    for f in AGENTS.glob("*.md"):
        first = next((line for line in f.read_text().splitlines() if line.strip()), "")
        assert first.startswith("Role:"), f"{f.name} must start with `Role:`"
