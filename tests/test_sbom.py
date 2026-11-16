"""R43, R49: the SBOM covers the runtime dependencies and the optional extras, never the
dev tools."""

import json
from pathlib import Path

from tests._proc import run

REPO_ROOT = Path(__file__).resolve().parents[1]
DEV_ONLY = {"pytest", "pytest-cov", "ruff", "mypy", "pip-audit"}


def test_sbom_lists_the_extras_and_no_dev_only_package():
    result = run(
        [
            "uv",
            "export",
            "--locked",
            "--all-extras",
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
    assert "anthropic" in names
    assert not names & DEV_ONLY
