"""3.1.1: ruff's target-version matches the minimum Python in requires-python.

A higher target lets `ruff format` write syntax the minimum can't parse: under py314 it
removed the parentheses from `except (A, B):` (PEP 758), and 3.13 then failed on import.
"""

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_ruff_target_version_is_the_minimum_in_requires_python():
    match = re.fullmatch(r">=\s*(\d+)\.(\d+)", PYPROJECT["project"]["requires-python"])
    assert match, "requires-python must be a single >=X.Y floor"
    assert PYPROJECT["tool"]["ruff"]["target-version"] == f"py{match.group(1)}{match.group(2)}"
