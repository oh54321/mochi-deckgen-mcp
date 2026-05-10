from deckgen_mcp.registry import all_tools, all_prompts, all_resources


def test_all_tools_combine_local_mochi_sync():
    names = {t["name"] for t in all_tools()}
    assert any(n.startswith("local_") for n in names)
    assert any(n.startswith("mochi_") for n in names)
    assert any(n.startswith("sync_") for n in names)


def test_all_prompts_include_subagents_and_workflows():
    names = {p["name"] for p in all_prompts()}
    assert "card-verifier" in names
    assert "generate-deck" in names
    assert "quickstart" in names


def test_all_resources_include_subagent_files():
    uris = {r["uri"] for r in all_resources()}
    assert any("card-verifier" in u for u in uris)
