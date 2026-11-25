"""R30: the daily_post.py shim runs from the repo root with no install. A real
daily_post.py run with only the old AI_POST_* names set, built the way
tests/acceptance/conftest.py's env_builder builds its child environment, stops
with the old-name message: no data folder, no run.log, no provider request."""

import os
import socket
import sys
import threading
from pathlib import Path

from tests._proc import run

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_shim(env, *args):
    return run(
        [sys.executable, "daily_post.py", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def old_name_env(tmp_path, port):
    home = tmp_path / "home"
    home.mkdir()
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "AI_POST_DATA_DIR": str(tmp_path / "data"),
        "AI_POST_ENV_FILE": str(tmp_path / "env-file-does-not-exist"),
        "AI_POST_PROVIDER": "openai-compat",
        "OPENAI_COMPAT_BASE_URL": f"http://127.0.0.1:{port}/v1",
        "OPENAI_COMPAT_MODEL": "m",
        "OPENAI_COMPAT_API_KEY": "k",
    }


def test_topic_run_with_only_old_names_stops_before_anything_happens(tmp_path):
    connections = []
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()

    def accept():
        try:
            conn, _ = server.accept()
        except OSError:
            return  # closed with no connection
        connections.append(conn)
        conn.close()

    thread = threading.Thread(target=accept, daemon=True)
    thread.start()
    env = old_name_env(tmp_path, server.getsockname()[1])
    assert not [name for name in env if name.startswith("QC_POST_")]

    result = run_shim(env, "--topic", "x")

    server.close()
    thread.join(timeout=5)
    assert result.returncode == 1, result.stderr
    assert "Traceback" not in result.stdout + result.stderr
    assert result.stdout == ""
    assert "AI_POST_PROVIDER is no longer read; rename it to QC_POST_PROVIDER" in result.stderr
    assert "AI_POST_DATA_DIR is no longer read; rename it to QC_POST_DATA_DIR" in result.stderr
    assert "AI_POST_ENV_FILE is no longer read; rename it to QC_POST_ENV_FILE" in result.stderr
    assert 'Upgrading to 4.0" in the README' in result.stderr
    assert not (tmp_path / "data").exists()  # no folder, no run.log
    assert connections == []  # no provider was built or called


def test_help_with_only_old_names_still_works_and_writes_nothing(tmp_path):
    env = old_name_env(tmp_path, 9)

    result = run_shim(env, "--help")

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout
    assert result.stderr == ""
    assert not (tmp_path / "data").exists()
