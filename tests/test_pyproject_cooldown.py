"""The uv install cooldown: `exclude-newer = "7 days"` is the first key under [tool.uv].

pyproject.toml is read as text, not parsed: Semgrep reads the table only up to the first
bracket, so the key must come before any `[`, comment included.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
LOCK = REPO_ROOT / "uv.lock"


def tool_uv_lines() -> list[str]:
    """The lines after the exact `[tool.uv]` header, up to the next table header."""
    lines = PYPROJECT.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "[tool.uv]")
    body = []
    for line in lines[start + 1 :]:
        if line.lstrip().startswith("["):
            break
        body.append(line)
    return body


def first_key_index(body: list[str]) -> int:
    return next(i for i, line in enumerate(body) if line.strip() and not line.startswith("#"))


def test_exclude_newer_is_the_first_key_under_tool_uv_with_seven_days() -> None:
    body = tool_uv_lines()
    assert body[first_key_index(body)] == 'exclude-newer = "7 days"'


def test_no_bracket_between_the_header_and_exclude_newer() -> None:
    lines = PYPROJECT.read_text(encoding="utf-8").splitlines()
    start = lines.index("[tool.uv]")
    end = lines.index('exclude-newer = "7 days"', start)
    assert not any("[" in line or "]" in line for line in lines[start + 1 : end])


def test_the_lock_records_the_seven_day_span() -> None:
    assert re.search(r'^exclude-newer-span = "P7D"$', LOCK.read_text(encoding="utf-8"), re.M)
