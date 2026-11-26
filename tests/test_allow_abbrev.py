"""The command line rejects abbreviated flags instead of guessing them."""

import sys

import pytest

from questcast import cli


@pytest.fixture
def no_provider(monkeypatch):
    """A rejected flag must exit before any provider is chosen or called."""

    def fail(*args, **kwargs):
        pytest.fail("a provider was selected or called")

    monkeypatch.setattr(cli, "select_provider", fail)
    monkeypatch.setattr(cli, "make_provider", fail)


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--post-l"], "unrecognized arguments: --post-l"),
        (["--post-a"], "unrecognized arguments: --post-a"),
        # "--prov" is not taken as a flag, so "groq" is read as a command.
        (["--prov", "groq"], "invalid choice: 'groq'"),
        (["--list"], "unrecognized arguments: --list"),
    ],
)
def test_abbreviated_flag_exits_2(monkeypatch, capsys, no_provider, args, message):
    monkeypatch.setattr(sys, "argv", ["qc", *args])

    with pytest.raises(SystemExit) as exc:
        cli.main()

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

    def flags(args):
        return (args.post, args.post_linkedin, args.post_all, args.list_topics)

    assert flags(parser.parse_args(["--post"])) == (True, False, False, False)
    assert flags(parser.parse_args(["--post-linkedin"])) == (False, True, False, False)
    assert flags(parser.parse_args(["--post-all"])) == (False, False, True, False)
    assert flags(parser.parse_args(["--list-topics"])) == (False, False, False, True)

    args = parser.parse_args(["init"])
    assert args.command == "init"


def test_init_help_works(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["init", "--help"])

    assert exc.value.code == 0
    assert "usage:" in capsys.readouterr().out
