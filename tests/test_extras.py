"""R48: a missing optional SDK names how to install it, never a version."""

import re
import sys
import tomllib
from pathlib import Path

import pytest

from questcast import providers

REPO_ROOT = Path(__file__).resolve().parents[1]
EXTRAS = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
    "optional-dependencies"
]


def assert_no_version(message: str) -> None:
    # Pins live only in pyproject.toml, so Dependabot bumps need no text edits.
    assert not re.search(r"==\s*\d", message)
    for requirements in EXTRAS.values():
        for requirement in requirements:
            assert requirement.split("==")[1] not in message


def test_only_the_anthropic_extra_is_declared_and_pinned_exactly():
    assert set(EXTRAS) == {"anthropic"}
    assert [r.split("==")[0] for r in EXTRAS["anthropic"]] == ["anthropic"]
    assert all(r.count("==") == 1 for r in EXTRAS["anthropic"])


def test_missing_anthropic_names_its_extra_and_both_routes(monkeypatch):
    monkeypatch.setitem(sys.modules, "anthropic", None)
    with pytest.raises(SystemExit) as exc:
        providers.AnthropicProvider().generate("prompt")
    assert "--provider anthropic" in exc.value.code
    assert "uv tool install --reinstall '.[anthropic]'" in exc.value.code
    assert "~/.qc_post_venv/bin/pip install -e '.[anthropic]'" in exc.value.code
    assert "ai_post_venv" not in exc.value.code
    assert_no_version(exc.value.code)
