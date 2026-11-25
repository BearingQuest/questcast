"""QuestCast 4: only QC_POST_* names, ~/QuestCast and ~/.qc_post_env are read. An
old name (AI_POST_*, ~/XPosts, ~/.ai_post_env) is never read; the old-name check
stops the run instead, with names and paths only. HOME is always a temporary
directory (conftest.isolated)."""

import builtins
import os
import sys
from importlib import resources
from pathlib import Path

import pytest

from questcast import cli, config, storage
from tests.conftest import SENTINEL_KEY

EXAMPLE = resources.files("questcast").joinpath(config.EXAMPLE_PROFILE).read_bytes()
PROFILE = "## Topics\n- Cloud\n\n## Beat\nPractitioners.\n\n## Voice\nPlain.\n"

MOVE_DATA = "~/XPosts is no longer read; move it with: mv ~/XPosts ~/QuestCast"
MOVE_KEYS = "~/.ai_post_env is no longer read; rename it with: mv ~/.ai_post_env ~/.qc_post_env"


@pytest.fixture
def home(tmp_path):
    path = tmp_path / "home"
    path.mkdir()
    return path


@pytest.fixture
def defaults(monkeypatch):
    """No path override variables, so the default locations decide."""
    monkeypatch.delenv("QC_POST_DATA_DIR")
    monkeypatch.delenv("QC_POST_ENV_FILE")


def run_cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["qc", *args])
    cli.main()


def refused(monkeypatch, capsys, *args):
    """Run qc expecting the old-name stop; return its stderr."""
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, *args)
    assert exc.value.code == 1  # int code: main() logs only message exits
    captured = capsys.readouterr()
    assert captured.out == ""
    return captured.err


def tree(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


# ---------------------------------------------------------------------------
# Only QC_POST_* is read
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", config.SETTING_NAMES)
def test_setting_reads_only_the_new_name(monkeypatch, name):
    monkeypatch.delenv(f"QC_POST_{name}", raising=False)  # conftest sets two of them
    monkeypatch.setenv(f"AI_POST_{name}", "old")
    assert config.setting(name) is None

    monkeypatch.setenv(f"QC_POST_{name}", "new")
    assert config.setting(name) == "new"


def test_an_empty_new_name_still_counts_as_set(monkeypatch):
    monkeypatch.setenv("QC_POST_PROVIDER", "")
    assert config.setting("PROVIDER") == ""


def test_old_values_are_not_applied(monkeypatch):
    monkeypatch.setenv("AI_POST_PROVIDER", "anthropic")
    monkeypatch.setenv("AI_POST_PROVIDER_TIMEOUT", "5")
    monkeypatch.setenv("AI_POST_TOKEN_BUDGET", "1")

    assert config.provider_setting() == ""
    assert config.provider_timeout() == config.DEFAULT_PROVIDER_TIMEOUT
    assert config.token_budget() == config.DEFAULT_TOKEN_BUDGET


def test_default_locations_are_the_new_ones(home, defaults):
    (home / "XPosts").mkdir()
    (home / ".ai_post_env").write_text("")

    assert config.data_dir() == home / "QuestCast"
    assert config.env_file() == home / ".qc_post_env"
    assert not (home / "QuestCast").exists()  # nothing created


def test_overrides_win(monkeypatch, home, defaults):
    monkeypatch.setenv("QC_POST_DATA_DIR", "/new/data")
    monkeypatch.setenv("QC_POST_ENV_FILE", "/new/env")

    assert config.data_dir() == Path("/new/data")
    assert config.env_file() == Path("/new/env")


def test_new_file_values_load_and_the_shell_still_wins(monkeypatch, tmp_path):
    env_file = tmp_path / "my.env"
    env_file.write_text("QC_POST_PROVIDER=anthropic\nQC_POST_SEARCH=rss\n")
    monkeypatch.setenv("QC_POST_ENV_FILE", str(env_file))
    monkeypatch.setenv("QC_POST_PROVIDER", "groq")
    monkeypatch.setenv("QC_POST_SEARCH", "x")  # registered, so monkeypatch restores it
    monkeypatch.delenv("QC_POST_SEARCH")

    config.load_env_file()

    assert config.provider_setting() == "groq"
    assert config.search_setting() == "rss"


def test_env_file_location_cannot_be_set_inside_the_file(monkeypatch, home, defaults):
    (home / ".qc_post_env").write_text(f"QC_POST_ENV_FILE={home / 'a'}\n")

    config.load_env_file()

    assert config.env_file() == home / ".qc_post_env"
    assert "QC_POST_ENV_FILE" not in os.environ


# ---------------------------------------------------------------------------
# 2a: AI_POST_<NAME> set anywhere
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", config.SETTING_NAMES)
def test_each_old_setting_name_is_found(monkeypatch, name):
    monkeypatch.setenv(f"AI_POST_{name}", "x")

    assert config.old_name_problems() == [
        f"AI_POST_{name} is no longer read; rename it to QC_POST_{name}"
    ]


def test_old_and_new_both_set_still_stops(monkeypatch):
    monkeypatch.setenv("QC_POST_PROVIDER", "groq")
    monkeypatch.setenv("AI_POST_PROVIDER", "groq")

    assert config.old_name_problems() == [
        "AI_POST_PROVIDER is no longer read; rename it to QC_POST_PROVIDER"
    ]


def test_an_empty_old_name_stops(monkeypatch):
    monkeypatch.setenv("AI_POST_SEARCH", "")

    assert len(config.old_name_problems()) == 1


def test_a_name_that_is_not_a_setting_is_not_a_problem(monkeypatch):
    monkeypatch.setenv("AI_POST_MODEL", "x")

    assert config.old_name_problems() == []


def test_an_old_name_in_the_env_file_stops_and_is_not_applied(monkeypatch, tmp_path, capsys):
    env_file = tmp_path / "my.env"
    env_file.write_text("QC_POST_PROVIDER=anthropic\nAI_POST_RSS_PER_FEED=7\nAI_POST_ENV_FILE=x\n")
    monkeypatch.setenv("QC_POST_ENV_FILE", str(env_file))
    for key in ("AI_POST_RSS_PER_FEED", "AI_POST_ENV_FILE", "QC_POST_PROVIDER"):
        monkeypatch.setenv(key, "x")  # registered, so monkeypatch removes what the file adds
        monkeypatch.delenv(key)

    config.load_env_file()

    assert config.rss_per_feed() == config.DEFAULT_RSS_PER_FEED  # never applied
    assert config.old_name_problems() == [
        "AI_POST_RSS_PER_FEED is no longer read; rename it to QC_POST_RSS_PER_FEED",
        "AI_POST_ENV_FILE is no longer read; rename it to QC_POST_ENV_FILE",
    ]


# ---------------------------------------------------------------------------
# 2b, 2c: the old default paths
# ---------------------------------------------------------------------------


def test_old_data_folder_alone_stops(home, defaults):
    (home / "XPosts").mkdir()

    assert config.old_name_problems() == [MOVE_DATA + " (or set QC_POST_DATA_DIR)"]


def test_old_key_file_alone_stops(home, defaults):
    (home / ".ai_post_env").write_text("")

    assert config.old_name_problems() == [MOVE_KEYS + " (or set QC_POST_ENV_FILE)"]


def test_both_new_and_old_exist_is_quiet(home, defaults):
    (home / "XPosts").mkdir()
    (home / "QuestCast").mkdir()
    (home / ".ai_post_env").write_text("")
    (home / ".qc_post_env").write_text("")

    assert config.old_name_problems() == []


def test_a_path_override_makes_the_old_default_irrelevant(monkeypatch, home):
    (home / "XPosts").mkdir()  # QC_POST_DATA_DIR and QC_POST_ENV_FILE are set by conftest
    (home / ".ai_post_env").write_text("")

    assert config.old_name_problems() == []


def test_each_path_override_only_covers_its_own_path(monkeypatch, home, defaults):
    (home / "XPosts").mkdir()
    (home / ".ai_post_env").write_text("")
    monkeypatch.setenv("QC_POST_DATA_DIR", str(home / "d"))

    assert config.old_name_problems() == [MOVE_KEYS + " (or set QC_POST_ENV_FILE)"]


def test_the_data_dir_override_can_come_from_the_env_file(monkeypatch, home, defaults):
    (home / "XPosts").mkdir()
    (home / ".qc_post_env").write_text(f"QC_POST_DATA_DIR={home / 'd'}\n")
    monkeypatch.setenv("QC_POST_DATA_DIR", "x")  # registered, so it is removed afterwards
    monkeypatch.delenv("QC_POST_DATA_DIR")

    config.load_env_file()

    assert config.old_name_problems() == []


def test_neither_old_path_is_quiet(home, defaults):
    assert config.old_name_problems() == []


def test_everything_is_listed_in_one_message(monkeypatch, home, defaults, capsys):
    (home / "XPosts").mkdir()
    (home / ".ai_post_env").write_text("")
    monkeypatch.setenv("AI_POST_PROVIDER", "groq")
    monkeypatch.setenv("AI_POST_DATA_DIR", "/old")

    err = refused(monkeypatch, capsys, "--list-topics")

    lines = err.splitlines()
    assert lines[0].startswith("questcast: old names found")
    problems = [line for line in lines if line.startswith("  - ")]
    assert problems == [
        "  - AI_POST_PROVIDER is no longer read; rename it to QC_POST_PROVIDER",
        "  - AI_POST_DATA_DIR is no longer read; rename it to QC_POST_DATA_DIR",
        f"  - {MOVE_DATA} (or set QC_POST_DATA_DIR)",
        f"  - {MOVE_KEYS} (or set QC_POST_ENV_FILE)",
    ]
    assert 'Upgrading to 4.0" in the README' in lines[-1]


# ---------------------------------------------------------------------------
# What the stop touches: nothing
# ---------------------------------------------------------------------------


def test_values_are_never_printed(monkeypatch, home, defaults, capsys):
    (home / ".ai_post_env").write_text(f"GROQ_API_KEY={SENTINEL_KEY}\n")
    for name in config.SETTING_NAMES:
        monkeypatch.setenv(f"AI_POST_{name}", SENTINEL_KEY)

    err = refused(monkeypatch, capsys, "--topic", "x")

    assert SENTINEL_KEY not in err
    assert err.count("is no longer read") == len(config.SETTING_NAMES) + 1


def test_old_paths_are_never_opened_read_or_listed(monkeypatch, home, defaults, capsys):
    old_dir, old_keys = home / "XPosts", home / ".ai_post_env"
    old_dir.mkdir()
    (old_dir / "history.json").write_text("[]")
    old_keys.write_text(f"GROQ_API_KEY={SENTINEL_KEY}\n")
    touched = []

    def guard(real):
        def wrapper(self, *args, **kwargs):
            if old_dir in (self, *self.parents) or self == old_keys:
                touched.append(self)
            return real(self, *args, **kwargs)

        return wrapper

    for method in ("open", "read_text", "read_bytes", "iterdir", "unlink", "rename", "chmod"):
        monkeypatch.setattr(Path, method, guard(getattr(Path, method)))
    real_open = builtins.open

    def spy_open(file, *args, **kwargs):
        if str(file).startswith((str(old_dir), str(old_keys))):
            touched.append(file)
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy_open)

    refused(monkeypatch, capsys, "--list-topics")

    assert touched == []
    assert old_keys.read_text() == f"GROQ_API_KEY={SENTINEL_KEY}\n"
    assert tree(old_dir) == ["history.json"]


@pytest.mark.parametrize(
    "args", [(), ("--topic", "x"), ("--list-topics",), ("--history",), ("init",)]
)
def test_every_command_stops_and_writes_nothing(monkeypatch, home, defaults, capsys, args):
    (home / "XPosts").mkdir()
    (home / "XPosts" / "author_profile.md").write_text(PROFILE)
    before = tree(home)

    err = refused(monkeypatch, capsys, *args)

    assert MOVE_DATA in err
    assert tree(home) == before  # no ~/QuestCast, no run.log, nothing moved
    assert (home / "XPosts" / "author_profile.md").read_text() == PROFILE


def test_the_stop_writes_no_run_log_and_does_not_create_the_data_dir(monkeypatch, tmp_path, capsys):
    data = tmp_path / "data"
    monkeypatch.setenv("QC_POST_DATA_DIR", str(data))
    monkeypatch.setenv("AI_POST_PROVIDER", "groq")
    monkeypatch.setattr(storage, "RUN_VIA", "")

    refused(monkeypatch, capsys, "--topic", "x")

    assert not data.exists()


def test_no_provider_is_built(monkeypatch, capsys):
    def fail(*args, **kwargs):
        pytest.fail("a provider was selected or built")

    monkeypatch.setattr(cli, "select_provider", fail)
    monkeypatch.setattr(cli, "make_provider", fail)
    monkeypatch.setenv("AI_POST_PROVIDER", "groq")

    refused(monkeypatch, capsys, "--topic", "x")


def test_help_still_works_with_old_names_set(monkeypatch, capsys):
    monkeypatch.setenv("AI_POST_PROVIDER", "groq")
    monkeypatch.setattr(sys, "argv", ["qc", "--help"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
    assert "usage:" in capsys.readouterr().out


def test_new_names_alone_run_quietly(monkeypatch, home, defaults, profile_file, capsys):
    (home / "QuestCast").mkdir()
    (home / "QuestCast" / "author_profile.md").write_text(profile_file.read_text())
    (home / ".qc_post_env").write_text("")

    run_cli(monkeypatch, "--list-topics")

    assert capsys.readouterr().err == ""


# ---------------------------------------------------------------------------
# Path display
# ---------------------------------------------------------------------------


def test_shown_strips_control_characters_and_abbreviates_home(home):
    assert config.shown(home / "XPosts") == "~/XPosts"
    assert config.shown(home) == "~"
    dirty = config.shown(Path("/a/\x1b[31mb\nc\u2028d\u2029e\x85f"))
    assert not config.CONTROL_CHARS.search(dirty)
    assert dirty == "/a/ [31mb c d e f"


def test_a_home_with_control_characters_gives_a_clean_message(
    monkeypatch, tmp_path, defaults, capsys
):
    weird = tmp_path / "ho\x1b[31mme\nx"
    (weird / "XPosts").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(weird))

    err = refused(monkeypatch, capsys, "--list-topics")

    assert "\x1b" not in err
    assert MOVE_DATA in err
