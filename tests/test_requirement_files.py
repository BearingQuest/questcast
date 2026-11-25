"""R29, R36, R44, R46, R47: the files that carry these requirements still say what they must.

Text-level checks, like tests/test_workflows.py: they read the Makefile, two workflows,
dependabot.yml and SECURITY.md and fail if the requirement's words go missing.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def recipe(target: str) -> list[str]:
    lines = text(REPO_ROOT / "Makefile").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{target}:"))
    body = []
    for line in lines[start + 1 :]:
        if not line.startswith("\t"):
            break
        body.append(line.strip())
    return body


def test_r29_make_check_fails_below_the_85_percent_coverage_floor():
    """R29: `make check` measures the package and fails under 85%."""
    pytest_lines = [line for line in recipe("check") if "pytest" in line]
    assert len(pytest_lines) == 1
    assert "--cov=questcast" in pytest_lines[0]
    assert "--cov-fail-under=85" in pytest_lines[0]


def test_r36_daily_pip_audit_runs_on_a_schedule_and_by_hand():
    """R36: audit-daily.yml has an off-the-hour daily schedule, workflow_dispatch and the
    pip-audit command, under a job name that differs from the required `pip-audit` check."""
    body = text(WORKFLOWS / "audit-daily.yml")
    crons = re.findall(r'cron: "(\d+) (\d+) \* \* \*"', body)
    assert len(crons) == 1
    assert crons[0][0] != "0"  # off the hour
    assert re.search(r"^  workflow_dispatch:", body, re.MULTILINE)
    assert re.search(r"^ {8}run: make audit$", body, re.MULTILINE)
    assert re.search(r"^ {4}name: pip-audit \(daily\)$", body, re.MULTILINE)
    audit = " ".join(recipe("audit"))
    assert "pip-audit --strict --disable-pip" in audit
    assert "--all-extras" in audit  # the whole lock, extras included


def test_r44_dependabot_covers_uv_and_github_actions_with_a_cooldown():
    """R44: weekly version updates for uv and github-actions, a 7-day cooldown on each,
    and minor and patch updates grouped."""
    body = text(REPO_ROOT / ".github" / "dependabot.yml")
    assert re.findall(r"package-ecosystem: (\S+)", body) == ["uv", "github-actions"]
    assert re.findall(r"interval: (\S+)", body) == ["weekly", "weekly"]
    assert re.findall(r"default-days: (\d+)", body) == ["7", "7"]
    assert body.count("update-types: [minor, patch]") == 2


def test_r46_sbom_workflow_writes_the_sbom_and_uploads_it():
    """R46: on every push to master, `make sbom` runs and build/sbom.cdx.json is kept as the
    artifact sbom-<commit SHA>; never on pull requests."""
    body = text(WORKFLOWS / "sbom.yml")
    assert re.search(r"^  push:\n    branches: \[master\]$", body, re.MULTILINE)
    assert "pull_request" not in body
    assert re.search(r"^ {8}run: make sbom$", body, re.MULTILINE)
    assert "uses: actions/upload-artifact@" in body
    assert "name: sbom-${{ github.sha }}" in body
    assert re.search(r"^ {10}path: build/sbom\.cdx\.json$", body, re.MULTILINE)
    assert "if-no-files-found: error" in body
    assert any("--output-file build/sbom.cdx.json" in line for line in recipe("sbom"))


def test_r47_security_md_describes_private_reporting_and_supported_versions():
    """R47: SECURITY.md says how to report privately and which versions are supported."""
    body = " ".join(text(REPO_ROOT / "SECURITY.md").split())
    assert "## Reporting a vulnerability" in body
    assert "Report a vulnerability" in body
    assert "Don't open a public issue" in body
    assert "## Supported versions" in body
    assert "Only the latest release is supported (4.x today)." in body
    assert (
        "Security fixes land on `master` and ship in the next release, which is what users install."
        in body
    )
    assert "There are no tagged releases yet." not in body
