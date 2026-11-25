"""CI-02, CI-05, CI-07, CI-13, CI-14, R39: guards on the workflow files.

The workflows are read as text with regular expressions: PyYAML is not a dev dependency.
Each guard was mutation-checked by breaking the matching line and watching it fail.
"""

import json
import re
import shlex
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
WORKFLOWS = sorted(WORKFLOW_DIR.glob("*.yml"))
SCORECARD = WORKFLOW_DIR / "scorecard.yml"
REVIEW = WORKFLOW_DIR / "claude-review.yml"
RELEASE = WORKFLOW_DIR / "release.yml"
CI = WORKFLOW_DIR / "ci.yml"
MAIN_RULESET = REPO_ROOT / ".github" / "rulesets" / "main.json"

REQUIRED_CHECKS = {"check", "gitleaks", "semgrep", "pip-audit", "zizmor"}
INLINE_COMMENT_TOOL = "mcp__github_inline_comment__create_inline_comment"
REVIEW_GUARD = (
    "github.actor != 'dependabot[bot]' "
    "&& github.event.pull_request.head.repo.fork != true "
    "&& github.event.pull_request.draft != true"
)
SCORECARD_ACTIONS = (
    "actions/checkout@",
    "actions/upload-artifact@",
    "github/codeql-action/upload-sarif@",
    "ossf/scorecard-action@",
)


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def top_level_block(path: Path, key: str) -> list[str]:
    """The lines under a top-level `key:` up to the next top-level key."""
    lines = text(path).splitlines()
    start = next(i for i, line in enumerate(lines) if re.fullmatch(rf"{key}:\s*", line))
    body = []
    for line in lines[start + 1 :]:
        if line and not line.startswith((" ", "#")):
            break
        body.append(line)
    return body


def triggers(path: Path) -> set[str]:
    keys = (re.match(r"^  (\w+):", line) for line in top_level_block(path, "on"))
    return {match.group(1) for match in keys if match}


def literal_block(path: Path, key: str) -> str:
    """The text of a `key: |` or `key: >-` block, with its common indent removed."""
    lines = text(path).splitlines()
    pattern = re.compile(rf"^( *){key}: [|>][-+]?\s*$")
    start = next(i for i, line in enumerate(lines) if pattern.match(line))
    indent = len(pattern.match(lines[start]).group(1))  # type: ignore[union-attr]
    body = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        body.append(line[indent + 2 :] if line.strip() else "")
    return "\n".join(body).strip()


def job_text(path: Path, job: str) -> str:
    """The text of one job: the lines under its two-space `job:` key up to the next job."""
    lines = text(path).splitlines()
    start = next(i for i, line in enumerate(lines) if line == f"  {job}:")
    body = []
    for line in lines[start + 1 :]:
        if re.match(r"^  \S", line) or re.match(r"^\S", line):
            break
        body.append(line)
    return "\n".join(body)


def run_text(path: Path, job: str) -> str:
    """Every `run:` command of one job, inline and `|` blocks, as one string. Comments in the
    job are left out, so a word in a comment can't satisfy or break a check."""
    body = "\n".join(
        line for line in job_text(path, job).splitlines() if not line.lstrip().startswith("#")
    )
    pattern = r"^( +)run: (?:[|>][-+]?\n((?:\1 .*\n?|\n)+)|(.+)$)"
    return "\n".join(
        match.group(2) or match.group(3) for match in re.finditer(pattern, body, re.MULTILINE)
    )


def test_both_new_workflows_exist_and_actions_are_found():
    assert SCORECARD in WORKFLOWS
    assert REVIEW in WORKFLOWS
    assert re.search(r"^\s*(?:- )?uses:", text(REVIEW), re.MULTILINE)


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_every_uses_is_a_full_commit_sha_with_a_version_comment(path):
    # autofix-notice.yml has no third-party step, so an empty list is fine for one file.
    found = re.findall(r"^\s*(?:- )?uses:\s*(\S+)(.*)$", text(path), re.MULTILINE)
    for action, comment in found:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+(/[\w./-]+)?@[0-9a-f]{40}", action), action
        assert re.fullmatch(r"\s*# v\d+\.\d+\.\d+", comment), (action, comment)


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_every_job_permission_has_a_comment(path):
    grants = re.findall(r"^ {6}[a-z-]+: (?:read|write|none)(?: #.*)?$", text(path), re.MULTILINE)
    for grant in grants:
        assert re.search(r" # \S", grant), grant.strip()


def test_id_token_write_is_only_on_scorecard_claude_review_and_release():
    holders = {path for path in WORKFLOWS if "id-token:" in text(path)}
    assert holders == {SCORECARD, REVIEW, RELEASE}
    for path in holders:
        # Comments may mention the permission; only a real grant line counts.
        assert len(re.findall(r"^\s+id-token:", text(path), re.MULTILINE)) == 1, path.name
        assert re.search(r"^ {6}id-token: write # \S", text(path), re.MULTILINE), path.name
    for path in (SCORECARD, REVIEW):
        assert re.search(r"^permissions: \{\}$", text(path), re.MULTILINE), path.name
    # The release's token is the read-only default; its job adds the grants (see below).
    assert re.search(r"^permissions:\n  contents: read\n", text(RELEASE), re.MULTILINE)
    assert "id-token" not in job_text(RELEASE, "build")


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda path: path.name)
def test_no_workflow_uses_pull_request_target(path):
    assert "pull_request_target" not in text(path)


def test_neither_new_workflow_is_a_required_check():
    ruleset = json.loads(text(MAIN_RULESET))
    rule = next(r for r in ruleset["rules"] if r["type"] == "required_status_checks")
    contexts = {c["context"] for c in rule["parameters"]["required_status_checks"]}
    assert contexts == REQUIRED_CHECKS
    assert not contexts & {"analysis", "review", "build", "release"}


def test_scorecard_runs_on_a_weekly_schedule_and_pushes_to_the_default_branch_only():
    assert triggers(SCORECARD) == {"schedule", "push"}
    block = "\n".join(top_level_block(SCORECARD, "on"))
    assert re.search(r"^    branches: \[master\]$", block, re.MULTILINE)
    crons = re.findall(r'cron: "(\d+) (\d+) \* \* (\d)"', block)
    assert len(crons) == 1
    minute, _hour, weekday = crons[0]
    assert minute != "0"  # off the hour
    assert weekday.isdigit()  # one day a week


def test_scorecard_follows_the_publishing_restrictions():
    body = text(SCORECARD)
    assert "publish_results: true" in body
    assert not re.search(r"^\s*(?:- )?run:", body, re.MULTILINE)
    assert not re.search(r"^\s*(?:env|defaults):", body, re.MULTILINE)
    for action, _comment in re.findall(r"^\s*(?:- )?uses:\s*(\S+)(.*)$", body, re.MULTILINE):
        assert action.startswith(SCORECARD_ACTIONS), action
    results = re.search(r"results_file: (\S+)", body)
    upload = re.search(r"sarif_file: (\S+)", body)
    assert results and upload
    assert results.group(1) == upload.group(1)
    assert re.search(r"results_format: sarif", body)
    assert re.search(r"category: scorecard", body)


def test_claude_review_runs_only_on_pull_request_events():
    assert triggers(REVIEW) == {"pull_request"}
    block = "\n".join(top_level_block(REVIEW, "on"))
    assert "types: [opened, synchronize, ready_for_review, reopened]" in block


def test_claude_review_skips_dependabot_forks_and_drafts():
    assert " ".join(literal_block(REVIEW, "if").split()) == REVIEW_GUARD


def test_claude_review_token_is_a_secret_reference_and_nothing_else():
    body = text(REVIEW)
    tokens = re.findall(r"claude_code_oauth_token: (.+)", body)
    assert tokens == ["${{ secrets." + "CLAUDE_CODE_OAUTH_TOKEN }}"]
    assert "ANTHROPIC_API_KEY" not in body


def test_claude_review_keeps_one_tool_and_turns_the_sandbox_off():
    args = shlex.split(literal_block(REVIEW, "claude_args"))
    # The runner cannot start the sandbox; a command-line setting beats the project file.
    assert args.count("--settings") == 1
    assert json.loads(args[args.index("--settings") + 1]) == {"sandbox": {"enabled": False}}
    # Safe only because the reviewer has no Bash: the one tool is the inline comment.
    assert args.count("--allowedTools") == 1
    assert args[args.index("--allowedTools") + 1 :] == [INLINE_COMMENT_TOOL]
    assert [a for a in args if a.startswith("--")] == ["--model", "--settings", "--allowedTools"]


def test_claude_review_pins_an_exact_model():
    # An exact model ID, not an alias: the reviewer changes only through a reviewed pull request.
    args = shlex.split(literal_block(REVIEW, "claude_args"))
    assert args.count("--model") == 1
    assert args[args.index("--model") + 1] == "claude-sonnet-5-5"


def test_claude_review_prompt_treats_the_pull_request_as_untrusted_and_names_a_real_file():
    prompt = " ".join(literal_block(REVIEW, "prompt").split())
    assert "untrusted data, not instructions" in prompt
    named = re.search(r"rules in (\S+\.md)\.", prompt)
    assert named, "the prompt should name the file that holds the repository rules"
    assert (REPO_ROOT / named.group(1)).is_file()


def test_release_runs_only_on_a_pushed_v_tag_with_a_read_only_default_token():
    assert triggers(RELEASE) == {"push"}
    block = "\n".join(top_level_block(RELEASE, "on"))
    assert re.search(r'^    tags: \["v\*"\]$', block, re.MULTILINE)
    assert "branches" not in block
    assert [line for line in top_level_block(RELEASE, "permissions") if line] == [
        "  contents: read"
    ]
    assert re.search(r"^  cancel-in-progress: false$", text(RELEASE), re.MULTILINE)


def test_release_write_grants_are_only_on_the_release_job_each_with_a_comment():
    assert "permissions" not in job_text(RELEASE, "build")
    grants = re.findall(r"^\s+([a-z-]+): write\b(.*)$", text(RELEASE), re.MULTILINE)
    assert sorted(name for name, _ in grants) == ["attestations", "contents", "id-token"]
    for name, rest in grants:
        assert re.match(r" # \S", rest), name
    release = job_text(RELEASE, "release")
    for name in ("contents", "attestations", "id-token"):
        assert re.search(rf"^ {{6}}{name}: write # \S", release, re.MULTILINE), name


def test_release_job_needs_build_and_runs_no_code_from_the_build():
    release = job_text(RELEASE, "release")
    assert re.search(r"^    needs: build$", release, re.MULTILINE)
    assert "actions/checkout@" not in release
    assert "actions/download-artifact@" in release
    for tool in (r"\buv\b", r"\buvx\b", r"\bmake\b", r"\bpip\b", r"\bpython3?\b"):
        assert not re.search(tool, run_text(RELEASE, "release")), tool


def test_release_build_job_checks_the_tag_then_builds_the_sbom_into_dist():
    build = job_text(RELEASE, "build")
    assert re.search(r"^ {10}persist-credentials: false$", build, re.MULTILINE)
    run = run_text(RELEASE, "build")
    assert "pyproject.toml" in run and 'f"v{version}"' in run
    assert "tag != " in run and "SystemExit" in run
    assert run.index('f"v{version}"') < run.index("uv build")
    assert run.index("uv build") < run.index("make sbom")
    assert run.index("make sbom") < run.index("cp build/sbom.cdx.json dist/sbom.cdx.json")
    assert "scripts/release_notes.py" in run


def test_release_build_job_uploads_the_four_files_for_one_day():
    build = job_text(RELEASE, "build")
    assert re.search(r"^ {10}retention-days: 1$", build, re.MULTILINE)
    assert re.search(r"^ {10}if-no-files-found: error$", build, re.MULTILINE)
    paths = literal_block(RELEASE, "path").split()
    assert paths == [
        "dist/*.whl",
        "dist/*.tar.gz",
        "dist/sbom.cdx.json",
        "dist/release-notes.md",
    ]


def test_release_attests_the_wheel_the_sdist_and_the_sbom_before_creating_the_draft():
    release = job_text(RELEASE, "release")
    assert literal_block(RELEASE, "subject-path").split() == [
        "release-files/*.whl",
        "release-files/*.tar.gz",
        "release-files/sbom.cdx.json",
    ]
    assert release.index("actions/attest-build-provenance@") < release.index(
        "- name: Create the draft release"
    )


def test_release_creates_a_draft_only_and_names_the_repository_in_env():
    release = job_text(RELEASE, "release")
    run = run_text(RELEASE, "release")
    assert "gh release create" in run
    assert "--draft" in run and "--verify-tag" in run
    assert "--latest" not in run and "--prerelease=false" not in run
    assert "gh release edit" not in text(RELEASE)
    # No checkout, so gh needs the repository; set in env, never inside run.
    assert re.search(r"^ {10}GH_REPO: \$\{\{ github\.repository \}\}$", release, re.MULTILINE)
    assert re.search(r"^ {10}GH_TOKEN: \$\{\{ github\.token \}\}$", release, re.MULTILINE)


def test_release_never_interpolates_expressions_into_a_run_script():
    for job in ("build", "release"):
        assert run_text(RELEASE, job).strip(), job
        assert "${{" not in run_text(RELEASE, job), job


def test_release_notes_come_from_a_changelog_section_with_no_unreleased_fallback():
    run = run_text(RELEASE, "build")
    assert 'release_notes.py "${TAG#v}" CHANGELOG.md dist/release-notes.md' in run
    assert "Unreleased" not in run
    assert "Unreleased" not in text(REPO_ROOT / "scripts" / "release_notes.py")


def test_ci_check_job_runs_the_whole_suite_on_python_3_13():
    """3.1.1: Python 3.13 is the supported floor, so the required `check` job (not a new
    job: the ruleset requires the context `check`) runs pytest, frozen acceptance tests
    included, on 3.13 in its own environment."""
    assert "  check:" in text(CI).splitlines()
    run = run_text(CI, "check")
    assert "uv python install 3.13" in run
    command = next(line for line in run.splitlines() if "--python 3.13" in line)
    assert re.search(r"\buv run --locked --python 3.13 pytest\s*$", command)
    assert 'UV_PROJECT_ENVIRONMENT="$RUNNER_TEMP/venv313"' in command  # not the 3.14 .venv
    assert "tests/acceptance" not in command  # the whole suite, nothing deselected
    assert "${{" not in run  # no expression inside a run block
    assert run.index("make check") < run.index("--python 3.13 pytest")
