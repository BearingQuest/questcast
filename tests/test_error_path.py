"""The error path never raises: an unwritable data folder gives a plain
message, and an unwritable run.log is one stderr line, never a second
traceback."""

import stat
import sys

import pytest

from questcast import cli, config, storage


def mode(path):
    return stat.S_IMODE(path.stat().st_mode)


@pytest.fixture
def blocked(monkeypatch, tmp_path):
    """A data directory that can't be created: its parent is a file."""
    blocker = tmp_path / "blocker"
    blocker.write_text("")
    data = blocker / "QuestCast"
    monkeypatch.setenv("QC_POST_DATA_DIR", str(data))
    return data


def test_log_run_reports_a_write_failure_instead_of_raising(blocked, capsys):
    storage.log_run("FAILED — something")

    err = capsys.readouterr().err
    assert err.count("\n") == 1
    assert "Could not write the run log" in err
    assert str(config.log_file()) in err


def test_init_names_the_path_the_reason_and_the_fix(monkeypatch, blocked, capsys):
    monkeypatch.setattr(sys, "argv", ["qc", "init"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    message = str(exc.value.code)
    assert str(blocked) in message
    assert "File exists" in message
    assert "QC_POST_DATA_DIR" in message
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert err.count("Could not write the run log") == 1


def test_a_failing_run_still_shows_the_original_error(monkeypatch, blocked, capsys):
    def boom():
        raise ValueError("the real problem")

    monkeypatch.setattr(cli, "run", boom)

    with pytest.raises(ValueError, match="the real problem"):
        cli.main()

    assert "Could not write the run log" in capsys.readouterr().err


def test_new_data_directory_gets_mode_700_under_a_permissive_umask(monkeypatch, tmp_path):
    import os

    data = tmp_path / "a" / "QuestCast"
    monkeypatch.setenv("QC_POST_DATA_DIR", str(data))
    old = os.umask(0o000)
    try:
        storage.ensure_data_dir()
    finally:
        os.umask(old)

    assert mode(data) == 0o700


def test_new_data_directory_is_mode_700_even_under_a_restrictive_umask(monkeypatch, tmp_path):
    import os

    data = tmp_path / "QuestCast"
    monkeypatch.setenv("QC_POST_DATA_DIR", str(data))
    old = os.umask(0o277)  # mkdir alone would leave 500: the owner couldn't write
    try:
        storage.ensure_data_dir()
    finally:
        os.umask(old)

    assert mode(data) == 0o700


def test_existing_data_directory_keeps_its_mode(monkeypatch, tmp_path):
    data = tmp_path / "QuestCast"
    data.mkdir()
    data.chmod(0o755)
    monkeypatch.setenv("QC_POST_DATA_DIR", str(data))

    storage.ensure_data_dir()

    assert mode(data) == 0o755


def test_log_run_creates_a_missing_folder_with_mode_700(monkeypatch, tmp_path):
    data = tmp_path / "fresh"
    monkeypatch.setenv("QC_POST_DATA_DIR", str(data))

    storage.log_run("OK")

    assert mode(data) == 0o700
    assert "OK" in (data / "run.log").read_text()
