from __future__ import annotations

import re
from pathlib import Path

SEPARATOR_RE = re.compile(r"(?m)^---\s*\n\s*\n")


def check_card_text(text: str) -> dict[str, object]:
    problems: list[str] = []
    matches = list(SEPARATOR_RE.finditer(text))
    if not matches:
        problems.append("Missing front/back separator (blank line + --- + blank line).")
        return {"valid": False, "problems": problems}

    if len(matches) > 1:
        problems.append("Multiple separators found; only the first is used.")

    front = text[: matches[0].start()].strip()
    back = text[matches[0].end() :].strip()
    if not front:
        problems.append("Empty front.")
    if not back:
        problems.append("Empty back.")

    valid = not any(p.startswith(("Empty", "Missing")) for p in problems)
    return {"valid": valid, "problems": problems}


def check_card_file(path: Path) -> dict[str, object]:
    return check_card_text(Path(path).read_text(encoding="utf-8"))
