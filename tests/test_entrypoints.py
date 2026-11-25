"""The qc command."""

import sys

import pytest

from questcast import cli


def test_qc_help_prints_usage(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["qc", "--help"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    assert "usage: qc" in capsys.readouterr().out
