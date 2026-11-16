"""R30: the daily_post.py shim runs from the repo root with no install. A real
daily_post.py run with only the old AI_POST_* names set, built the way
tests/acceptance/conftest.py's env_builder builds its child environment. The
frozen acceptance tests all do this, so this keeps the old-name path covered by
a test that is not frozen: the names still work, and each run says so once."""

import os
import sys
from pathlib import Path

from tests._proc import run

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_help_with_only_old_names_prints_the_deprecation_notice_once(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "AI_POST_DATA_DIR": str(tmp_path / "data"),
        "AI_POST_ENV_FILE": str(tmp_path / "env-file-does-not-exist"),
        "AI_POST_PROVIDER": "groq",
    }
    assert not [name for name in env if name.startswith("QC_POST_")]

    result = run(
        [sys.executable, "daily_post.py", "--help"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stdout + result.stderr
    assert "usage:" in result.stdout
    notices = [line for line in result.stderr.splitlines() if "deprecated" in line]
    assert notices == [
        "questcast: AI_POST_PROVIDER, AI_POST_DATA_DIR, AI_POST_ENV_FILE are deprecated; "
        "rename them to QC_POST_*. Old names stop working after the next release."
    ]
    assert result.stderr.count("questcast:") == 1
    assert not (tmp_path / "data").exists()  # --help writes nothing
