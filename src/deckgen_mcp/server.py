from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from deckgen_mcp.registry import AGENTS_DIR, all_prompts, all_resources, all_tools


def build_server() -> FastMCP:
    server = FastMCP("deckgen")

    for tool in all_tools():
        server.tool(name=tool["name"], description=tool["description"])(tool["fn"])

    def _make_prompt_fn(content: str):
        def fn() -> str:
            return content
        return fn

    for prompt in all_prompts():
        content = prompt["path"].read_text(encoding="utf-8")
        server.prompt(name=prompt["name"], description=prompt["description"])(
            _make_prompt_fn(content)
        )

    for resource in all_resources():
        text = Path(resource["path"]).read_text(encoding="utf-8")
        server.resource(
            uri=resource["uri"],
            name=resource["name"],
            mime_type=resource["mimeType"],
        )(_make_prompt_fn(text))

    return server


def main() -> None:
    parser = argparse.ArgumentParser(prog="deckgen-mcp")
    parser.add_argument(
        "--agents-path",
        action="store_true",
        help="Print the path to the bundled .claude/agents/ directory and exit.",
    )
    args = parser.parse_args()

    if args.agents_path:
        repo_agents = Path(__file__).parent.parent.parent / ".claude" / "agents"
        if repo_agents.exists():
            print(repo_agents.resolve())
        else:
            print(AGENTS_DIR.resolve())
        sys.exit(0)

    build_server().run()


if __name__ == "__main__":
    main()
