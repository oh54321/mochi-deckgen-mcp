from pathlib import Path

from mochi_tools_mcp.local.malformed_check import check_card_text


def test_well_formed_card():
    text = "What is 2+2?\n\n---\n\n4\n"
    result = check_card_text(text)
    assert result["valid"] is True
    assert result["problems"] == []


def test_missing_separator():
    text = "What is 2+2?\n\n4\n"
    result = check_card_text(text)
    assert result["valid"] is False
    assert "separator" in result["problems"][0].lower()


def test_empty_front():
    text = "\n---\n\n4\n"
    result = check_card_text(text)
    assert result["valid"] is False
    assert any("front" in p.lower() for p in result["problems"])


def test_empty_back():
    text = "What is 2+2?\n\n---\n\n\n"
    result = check_card_text(text)
    assert result["valid"] is False
    assert any("back" in p.lower() for p in result["problems"])


def test_multiple_separators_is_warning_not_error():
    text = "Q\n\n---\n\nA1\n\n---\n\nA2\n"
    result = check_card_text(text)
    assert result["valid"] is True
    assert any("separator" in p.lower() for p in result["problems"])


def test_check_file(tmp_path: Path):
    p = tmp_path / "card-001.md"
    p.write_text("Q\n\n---\n\nA\n")
    from mochi_tools_mcp.local.malformed_check import check_card_file

    assert check_card_file(p)["valid"] is True
