"""R35, R37, CI-01, CI-08, DOC-04: the ruleset files match the workflows and keep the gates.

The files in .github/rulesets/ are applied by Dusten; nothing here calls GitHub. A required
check that no job produces would block every merge, so each context must be a job name.
R35 and R37 (the security workflow's gitleaks, semgrep and pip-audit jobs) are covered here
as far as their job names go: each is a required check that a job produces.
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RULESETS = REPO_ROOT / ".github" / "rulesets"
WORKFLOWS = sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))

REQUIRED_CHECKS = {"check", "gitleaks", "semgrep", "pip-audit", "zizmor"}
GITHUB_ACTIONS_APP = 15368


def load(name: str) -> dict:
    return json.loads((RULESETS / name).read_text(encoding="utf-8"))


def rules(ruleset: dict) -> dict:
    return {rule["type"]: rule.get("parameters") for rule in ruleset["rules"]}


def job_names() -> set[str]:
    """Names of every job, read from the `name:` line under each `jobs:` entry."""
    names = set()
    for path in WORKFLOWS:
        in_jobs = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"^jobs:\s*$", line):
                in_jobs = True
            elif in_jobs and (match := re.match(r"^    name: (.+?)\s*$", line)):
                names.add(match.group(1).strip("\"'"))
    return names


def test_main_requires_the_five_checks_from_github_actions():
    params = rules(load("main.json"))["required_status_checks"]
    checks = params["required_status_checks"]
    assert {check["context"] for check in checks} == REQUIRED_CHECKS
    assert {check["integration_id"] for check in checks} == {GITHUB_ACTIONS_APP}
    assert params["strict_required_status_checks_policy"] is True


def test_every_required_check_is_a_job_name():
    assert job_names() >= REQUIRED_CHECKS


def test_main_keeps_the_branch_gates():
    ruleset = load("main.json")
    assert ruleset["enforcement"] == "active"
    assert ruleset["bypass_actors"] == []
    assert ruleset["conditions"]["ref_name"]["include"] == ["~DEFAULT_BRANCH"]
    by_type = rules(ruleset)
    for rule_type in ("deletion", "non_fast_forward", "required_linear_history", "code_scanning"):
        assert rule_type in by_type
    pull_request = by_type["pull_request"]
    assert pull_request["allowed_merge_methods"] == ["squash"]
    assert pull_request["required_approving_review_count"] == 0
    assert pull_request["required_review_thread_resolution"] is True
    tool = by_type["code_scanning"]["code_scanning_tools"][0]
    assert tool["tool"] == "CodeQL"
    assert tool["security_alerts_threshold"] == "high_or_higher"


def test_release_tags_protects_version_tags():
    ruleset = load("release-tags.json")
    assert ruleset["target"] == "tag"
    assert ruleset["enforcement"] == "active"
    assert ruleset["bypass_actors"] == []
    assert ruleset["conditions"]["ref_name"]["include"] == ["refs/tags/v*"]
    assert set(rules(ruleset)) == {"deletion", "non_fast_forward", "update"}


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_workflow_images_and_timeouts(path):
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"runs-on:\s*\S*-latest", text)
    assert text.count("timeout-minutes:") == text.count("runs-on:")


def test_zizmor_job_is_pinned_and_fails_on_findings():
    text = (REPO_ROOT / ".github" / "workflows" / "security.yml").read_text(encoding="utf-8")
    assert re.search(r"uvx --exclude-newer \d{4}-\d{2}-\d{2} zizmor@\d+\.\d+\.\d+ \.github", text)
