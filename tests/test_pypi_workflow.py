"""R76, R78: guards on .github/workflows/pypi.yml.

Read as text with the helpers in test_workflows.py: PyYAML is not a dev dependency, and adding it
would change uv.lock. Each guard was mutation-checked by breaking the matching line.
"""

import re

from tests.test_workflows import (
    PYPI,
    job_text,
    run_text,
    text,
    top_level_block,
    triggers,
)

SHA_PIN = "7245906fb61fa33a13554f9d5fb856fe61758086"
SIGNER = "BearingQuest/questcast/.github/workflows/release.yml"
PUBLISH_JOBS = {
    "publish-pypi": ("pypi", "https://pypi.org/p/questcast", "release"),
    "publish-testpypi": ("testpypi", "https://test.pypi.org/p/questcast", "workflow_dispatch"),
}


def test_only_a_published_release_and_a_manual_run_start_it() -> None:
    assert triggers(PYPI) == {"release", "workflow_dispatch"}
    block = "\n".join(top_level_block(PYPI, "on"))
    assert "types: [published]" in block
    assert re.search(r"^      tag:\n(?:        .*\n)*?        required: true$", block, re.MULTILINE)


def test_workflow_token_is_read_only_and_runs_never_cancel() -> None:
    assert [line for line in top_level_block(PYPI, "permissions") if line] == ["  contents: read"]
    assert re.search(r"^  cancel-in-progress: false$", text(PYPI), re.MULTILINE)
    assert re.search(r"^  group: pypi-\$\{\{ .*tag.* \}\}$", text(PYPI), re.MULTILINE)


def test_fetch_has_no_oidc_and_no_write_grant() -> None:
    fetch = job_text(PYPI, "fetch")
    assert "id-token" not in fetch
    assert not re.search(r": write\b", fetch)
    assert "actions/checkout@" not in fetch


def test_each_publish_job_has_exactly_the_oidc_grant_its_environment_and_condition() -> None:
    for job, (environment, url, event) in PUBLISH_JOBS.items():
        body = job_text(PYPI, job)
        grants = re.findall(r"^ {6}([a-z-]+): (\w+)", body.split("    permissions:\n", 1)[1], re.M)
        assert grants == [("id-token", "write")], job
        assert re.search(
            rf"^    environment:\n      name: {environment}\n      url: {re.escape(url)}$",
            body,
            re.M,
        ), job
        assert re.search(rf"^    if: github\.event_name == '{event}'$", body, re.MULTILINE), job
        assert re.search(r"^    needs: fetch$", body, re.MULTILINE), job


def test_publish_jobs_only_download_and_upload() -> None:
    for job in PUBLISH_JOBS:
        body = job_text(PYPI, job)
        assert not re.search(r"^\s*(?:- )?run:", body, re.MULTILINE), job
        for tool in ("actions/checkout@", "setup-uv", r"\buv\b", r"\bmake\b", r"\bpip\b", r"build"):
            assert not re.search(tool, run_text(PYPI, job) + re.sub(r"#.*", "", body)), (job, tool)
        uses = re.findall(r"^\s*- uses: (\S+)", body, re.MULTILINE)
        assert [u.split("@")[0] for u in uses] == [
            "actions/download-artifact",
            "pypa/gh-action-pypi-publish",
        ], job
        assert f"pypa/gh-action-pypi-publish@{SHA_PIN} # v1.14.3" in body
        assert re.search(r"^ {10}print-hash: true$", body, re.MULTILINE), job


def test_only_testpypi_sets_a_repository_url() -> None:
    assert not re.search(r"repository-url", job_text(PYPI, "publish-pypi"))
    testpypi = job_text(PYPI, "publish-testpypi")
    assert re.search(r"^ {10}repository-url: https://test\.pypi\.org/legacy/$", testpypi, re.M)


def test_the_tag_reaches_the_shell_only_through_env() -> None:
    assert re.search(
        r"^      TAG: \$\{\{ github\.event\.release\.tag_name \|\| inputs\.tag \}\}$",
        job_text(PYPI, "fetch"),
        re.MULTILINE,
    )
    run = run_text(PYPI, "fetch")
    assert "${{" not in run
    assert "$TAG" in run
    assert "${{" not in "".join(run_text(PYPI, j) for j in PUBLISH_JOBS)


def test_fetch_checks_the_tag_the_draft_flag_and_downloads_only_the_two_files() -> None:
    run = run_text(PYPI, "fetch")
    assert r"^v[0-9]+\.[0-9]+\.[0-9]+$" in run
    assert "gh release view" in run and "isDraft" in run
    assert "gh release download" in run
    assert "--pattern '*.whl' --pattern '*.tar.gz'" in run
    assert "sbom" not in run.lower() and "release-notes" not in run
    assert "sha256sum dist/*" in run


def test_fetch_verifies_every_file_against_release_yml_before_uploading() -> None:
    fetch = job_text(PYPI, "fetch")
    run = run_text(PYPI, "fetch")
    assert "gh attestation verify" in run
    assert f"--signer-workflow {SIGNER}" in run
    assert "-R BearingQuest/questcast" in run
    assert "for file in dist/*; do" in run
    assert fetch.index("gh attestation verify") < fetch.index("actions/upload-artifact@")
    assert fetch.index("gh attestation verify") < fetch.index("sha256sum")


def test_fetch_uploads_the_two_files_for_one_day() -> None:
    fetch = job_text(PYPI, "fetch")
    assert re.search(r"^ {10}retention-days: 1$", fetch, re.MULTILINE)
    assert re.search(r"^ {10}if-no-files-found: error$", fetch, re.MULTILINE)
    assert re.search(r"^ {10}path: dist/\*$", fetch, re.MULTILINE)


def test_download_and_publish_jobs_agree_on_the_artifact_name() -> None:
    names = re.findall(r"^ {10}name: (\S+)$", text(PYPI), re.MULTILINE)
    assert names == ["dist", "dist", "dist"]
