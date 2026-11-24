"""The command line rejects abbreviated flags instead of guessing them."""

import sys

import pytest

from questcast import cli

XGP_NOTICE = "xgp is now qc; xgp will be removed after the next release\n"


@pytest.fixture
def no_provider(monkeypatch):
    """A rejected flag must exit before any provider is chosen or called."""

    def fail(*args, **kwargs):
        pytest.fail("a provider was selected or called")

    monkeypatch.setattr(cli, "select_provider", fail)
    monkeypatch.setattr(cli, "make_provider", fail)


@pytest.mark.parametrize("entry", [cli.main, cli.xgp_main], ids=["qc", "xgp"])
@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--post-l"], "unrecognized arguments: --post-l"),
        # "--prov" is not taken as a flag, so "groq" is read as a command.
        (["--prov", "groq"], "invalid choice: 'groq'"),
        (["--list"], "unrecognized arguments: --list"),
    ],
)
def test_abbreviated_flag_exits_2(monkeypatch, capsys, no_provider, entry, args, message):
    monkeypatch.setattr(sys, "argv", ["qc", *args])

    with pytest.raises(SystemExit) as exc:
        entry()

    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "error:" in err
    assert message in err


def test_abbreviated_init_flag_exits_2(monkeypatch, capsys, no_provider):
    monkeypatch.setattr(sys, "argv", ["qc", "init", "--he"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err


def test_full_flags_still_parse():
    parser = cli.build_parser()

    args = parser.parse_args(["--post"])
    assert (args.post, args.post_linkedin, args.list_topics) == (True, False, False)

    args = parser.parse_args(["--post-linkedin"])
    assert (args.post, args.post_linkedin, args.list_topics) == (False, True, False)

    args = parser.parse_args(["--list-topics"])
    assert (args.post, args.post_linkedin, args.list_topics) == (False, False, True)

    args = parser.parse_args(["init"])
    assert args.command == "init"


def test_init_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["init", "--help"])

    assert exc.value.code == 0
    assert "usage:" in capsys.readouterr().out
