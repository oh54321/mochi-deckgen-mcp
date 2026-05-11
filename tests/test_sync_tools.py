from mochi_tools_mcp.tools import sync_tools


def test_collect_has_expected_tools():
    names = {t["name"] for t in sync_tools.collect()}
    assert names >= {"sync_push_deck", "sync_pull_deck", "sync_status", "sync_link"}


def test_push_without_auth(monkeypatch):
    monkeypatch.delenv("MOCHI_API_KEY", raising=False)
    tools = {t["name"]: t["fn"] for t in sync_tools.collect()}
    out = tools["sync_push_deck"](deck="X")
    assert out.get("isError") is True
