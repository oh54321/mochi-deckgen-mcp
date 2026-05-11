import asyncio
import subprocess
import sys
from pathlib import Path


def test_agents_path_flag():
    out = (
        subprocess.check_output([sys.executable, "-m", "deckgen_mcp.server", "--agents-path"])
        .decode()
        .strip()
    )
    p = Path(out)
    assert p.exists()
    assert p.is_dir()


def test_server_registers_all_tools_and_prompts():
    from deckgen_mcp.server import build_server

    server = build_server()

    tool_names = _extract_tool_names(server)
    assert "local_create_deck" in tool_names
    assert "mochi_list_decks" in tool_names
    assert "sync_push_deck" in tool_names

    prompt_names = _extract_prompt_names(server)
    assert "generate-deck" in prompt_names
    assert "card-verifier" in prompt_names


def _extract_tool_names(server) -> set:
    for attr in ("_tool_manager", "tool_manager"):
        mgr = getattr(server, attr, None)
        if mgr is not None:
            tools = mgr.list_tools() if hasattr(mgr, "list_tools") else mgr._tools.values()
            return {t.name for t in tools}
    if hasattr(server, "list_tools"):
        tools = asyncio.run(server.list_tools())
        return {t.name for t in tools}
    raise RuntimeError("Could not find tool list API on FastMCP")


def _extract_prompt_names(server) -> set:
    for attr in ("_prompt_manager", "prompt_manager"):
        mgr = getattr(server, attr, None)
        if mgr is not None:
            prompts = mgr.list_prompts() if hasattr(mgr, "list_prompts") else mgr._prompts.values()
            return {p.name for p in prompts}
    if hasattr(server, "list_prompts"):
        prompts = asyncio.run(server.list_prompts())
        return {p.name for p in prompts}
    raise RuntimeError("Could not find prompt list API on FastMCP")
