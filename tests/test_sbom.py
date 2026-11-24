"""R43: the SBOM covers the default install's runtime dependencies, never the dev tools or the
optional extras (supersedes R49, which put the anthropic extra in it)."""

import json
from pathlib import Path

from tests._proc import run

REPO_ROOT = Path(__file__).resolve().parents[1]
DEV_ONLY = {"pytest", "pytest-cov", "ruff", "mypy", "pip-audit"}


def test_sbom_covers_the_default_install_only_and_no_dev_only_package():
    result = run(
        [
            "uv",
            "export",
            "--locked",
            "--format",
            "cyclonedx1.5",
            "--no-dev",
            "--preview-features",
            "sbom-export",
            "--quiet",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    sbom = json.loads(result.stdout)
    assert sbom["metadata"]["component"]["name"] == "questcast"
    names = {component["name"] for component in sbom["components"]}
    assert "anthropic" not in names
    assert not names & DEV_ONLY


def test_make_sbom_exports_the_default_install_without_extras_or_dev_tools():
    lines = (REPO_ROOT / "Makefile").read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("sbom:"))
    recipe = []
    for line in lines[start + 1 :]:
        if not line.startswith("\t"):
            break
        recipe.append(line.strip())
    export = next(line for line in recipe if line.startswith("uv export"))
    assert "--locked" in export and "--no-dev" in export
    assert "--format cyclonedx1.5" in export
    assert "--all-extras" not in export and "--extra" not in export
