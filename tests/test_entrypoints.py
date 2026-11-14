"""The qc command, and xgp as a one-release alias for it."""

import sys

import pytest

from questcast import cli


def test_qc_help_prints_usage(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["qc", "--help"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    assert "usage: qc" in capsys.readouterr().out


def test_xgp_prints_notice_to_stderr_then_runs_qc(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "main", lambda: calls.append(list(sys.argv)))
    monkeypatch.setattr(sys, "argv", ["xgp", "--topic", "x"])

    cli.xgp_main()

    captured = capsys.readouterr()
    assert captured.err == "xgp is now qc; xgp will be removed after the next release\n"
    assert captured.out == ""
    assert calls == [["xgp", "--topic", "x"]]


def test_xgp_passes_exit_code_through(monkeypatch, capsys):
    def fail():
        raise SystemExit(3)

    monkeypatch.setattr(cli, "main", fail)

    with pytest.raises(SystemExit) as exc:
        cli.xgp_main()

    assert exc.value.code == 3
    assert "xgp is now qc" in capsys.readouterr().err


def test_xgp_help_matches_qc_help(monkeypatch, capsys):
    outputs = []
    for name, entry in (("qc", cli.main), ("xgp", cli.xgp_main)):
        monkeypatch.setattr(sys, "argv", [name, "--help"])
        with pytest.raises(SystemExit) as exc:
            entry()
        assert exc.value.code == 0
        outputs.append(
            "".join(
                capsys.readouterr().out.replace("qc", "<prog>").replace("xgp", "<prog>").split()
            )
        )

    assert outputs[0] == outputs[1]
