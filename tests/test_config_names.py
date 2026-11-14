"""PR B: QC_POST_* names, ~/QuestCast, ~/.qc_post_env, with the old names read as
fallbacks for one release. Every branch of the resolution rules, the stderr
notices, and qc init for each folder layout. HOME is always a temporary
directory (conftest.isolated)."""

import json
import os
import sys
from importlib import resources
from pathlib import Path

import pytest

from questcast import cli, config
from tests.conftest import MODEL_OUTPUT, SENTINEL_KEY, completion

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
EXAMPLE = resources.files("questcast").joinpath(config.EXAMPLE_PROFILE).read_bytes()
PROFILE = "## Topics\n- Cloud\n\n## Beat\nPractitioners.\n\n## Voice\nPlain.\n"


@pytest.fixture
def home(tmp_path):
    path = tmp_path / "home"
    path.mkdir()
    return path


@pytest.fixture
def defaults(monkeypatch):
    """No path override variables, so the default locations decide."""
    for prefix in ("QC_POST_", "AI_POST_"):
        monkeypatch.delenv(f"{prefix}DATA_DIR", raising=False)
        monkeypatch.delenv(f"{prefix}ENV_FILE", raising=False)


def run_cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["qc", *args])
    cli.run()


def stderr_lines(capsys):
    return [line for line in capsys.readouterr().err.splitlines() if line]


# ---------------------------------------------------------------------------
# Rule 1: variables
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("new", "old", "expected"),
    [
        ("30", None, 30.0),  # new only
        (None, "40", 40.0),  # old only
        ("30", "40", 30.0),  # both: new wins
        (None, None, config.DEFAULT_PROVIDER_TIMEOUT),  # neither
        ("", "40", config.DEFAULT_PROVIDER_TIMEOUT),  # set but empty still counts as set
    ],
)
def test_variable_resolution(monkeypatch, new, old, expected):
    if new is not None:
        monkeypatch.setenv("QC_POST_PROVIDER_TIMEOUT", new)
    if old is not None:
        monkeypatch.setenv("AI_POST_PROVIDER_TIMEOUT", old)

    assert config.provider_timeout() == expected


@pytest.mark.parametrize(
    ("new", "old", "expected"),
    [("groq", None, "groq"), (None, "anthropic", "anthropic"), ("groq", "anthropic", "groq")],
)
def test_string_setting_resolution(monkeypatch, new, old, expected):
    if new is not None:
        monkeypatch.setenv("QC_POST_PROVIDER", new)
    if old is not None:
        monkeypatch.setenv("AI_POST_PROVIDER", old)

    assert config.provider_setting() == expected


def test_whole_number_setting_falls_back_and_names_the_new_variable(monkeypatch):
    monkeypatch.setenv("AI_POST_TOKEN_BUDGET", "123")
    assert config.token_budget() == 123

    monkeypatch.setenv("AI_POST_TOKEN_BUDGET", "zero")
    with pytest.raises(SystemExit) as exc:
        config.token_budget()
    assert "QC_POST_TOKEN_BUDGET must be a whole number" in exc.value.code


def test_variable_notices(monkeypatch):
    assert config.legacy_notices() == []

    monkeypatch.setenv("QC_POST_SEARCH", "rss")
    assert config.legacy_notices() == []  # new names alone are silent

    monkeypatch.setenv("AI_POST_PROVIDER", "groq")
    assert config.legacy_notices() == [
        "questcast: AI_POST_PROVIDER is deprecated; rename it to QC_POST_*. "
        "Old names stop working after the next release."
    ]

    monkeypatch.setenv("AI_POST_MODEL", "x")  # not a setting: never listed
    monkeypatch.setenv("AI_POST_TOKEN_BUDGET", "9")
    assert config.legacy_notices() == [
        "questcast: AI_POST_PROVIDER, AI_POST_TOKEN_BUDGET are deprecated; rename them to "
        "QC_POST_*. Old names stop working after the next release."
    ]

    monkeypatch.setenv("QC_POST_PROVIDER", "groq")
    assert config.legacy_notices() == [
        "questcast: AI_POST_TOKEN_BUDGET is deprecated; rename it to QC_POST_*. "
        "Old names stop working after the next release.",
        "questcast: AI_POST_PROVIDER is ignored because QC_POST_PROVIDER is set",
    ]


def test_new_name_in_the_env_file_beats_old_name_in_the_shell(monkeypatch, tmp_path):
    env_file = tmp_path / "my.env"
    env_file.write_text("QC_POST_PROVIDER=anthropic\nAI_POST_RSS_PER_FEED=7\n")
    monkeypatch.setenv("QC_POST_ENV_FILE", str(env_file))
    monkeypatch.setenv("AI_POST_PROVIDER", "groq")

    config.load_env_file()

    assert config.provider_setting() == "anthropic"
    assert config.rss_per_feed() == 7  # an old name in the file works too
    assert config.legacy_notices() == [
        "questcast: AI_POST_RSS_PER_FEED is deprecated; rename it to QC_POST_*. "
        "Old names stop working after the next release.",
        "questcast: AI_POST_PROVIDER is ignored because QC_POST_PROVIDER is set",
    ]


def test_shell_still_beats_the_file_for_the_same_name(monkeypatch, tmp_path):
    env_file = tmp_path / "my.env"
    env_file.write_text("QC_POST_PROVIDER=anthropic\n")
    monkeypatch.setenv("QC_POST_ENV_FILE", str(env_file))
    monkeypatch.setenv("QC_POST_PROVIDER", "groq")

    config.load_env_file()

    assert config.provider_setting() == "groq"


# ---------------------------------------------------------------------------
# Rule 2: the credentials file
# ---------------------------------------------------------------------------


def test_env_file_override_variables_win_over_the_default_files(monkeypatch, home, defaults):
    (home / ".qc_post_env").write_text("")
    (home / ".ai_post_env").write_text("")

    monkeypatch.setenv("AI_POST_ENV_FILE", "/old/override")
    assert config.env_file() == Path("/old/override")  # AI_POST_ENV_FILE exists today

    monkeypatch.setenv("QC_POST_ENV_FILE", "/new/override")
    assert config.env_file() == Path("/new/override")
    assert config.legacy_notices() == [
        "questcast: AI_POST_ENV_FILE is ignored because QC_POST_ENV_FILE is set"
    ]


def test_env_file_override_makes_the_default_file_notices_moot(monkeypatch, home):
    (home / ".ai_post_env").write_text("")  # QC_POST_ENV_FILE is set by conftest

    assert config.legacy_notices() == []


def test_env_file_new_only(home, defaults):
    (home / ".qc_post_env").write_text("")

    assert config.env_file() == home / ".qc_post_env"
    assert config.legacy_notices() == []


def test_env_file_old_only(home, defaults):
    (home / ".ai_post_env").write_text("")

    assert config.env_file() == home / ".ai_post_env"
    assert config.legacy_notices() == [
        "questcast: using ~/.ai_post_env; rename it with: mv ~/.ai_post_env ~/.qc_post_env"
    ]


def test_env_file_both_new_wins_and_old_is_never_opened(monkeypatch, home, defaults):
    (home / ".qc_post_env").write_text("QC_POST_SEARCH=rss\n")
    (home / ".ai_post_env").write_text(
        f"AI_POST_PROVIDER=openai-compat\nGROQ_API_KEY={SENTINEL_KEY}\n"
    )
    opened = []
    real_read_text = Path.read_text

    def spy(self, *args, **kwargs):
        opened.append(self)
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy)

    config.load_env_file()

    assert config.env_file() == home / ".qc_post_env"
    assert opened == [home / ".qc_post_env"]
    assert config.search_setting() == "rss"
    assert config.provider_setting() == ""  # nothing from the old file
    assert config.legacy_notices() == [
        "questcast: ~/.ai_post_env is ignored because ~/.qc_post_env exists"
    ]


def test_env_file_neither_defaults_to_the_new_name(home, defaults):
    assert config.env_file() == home / ".qc_post_env"
    assert config.legacy_notices() == []


def test_env_file_location_cannot_be_set_inside_either_file(monkeypatch, home, defaults):
    (home / ".qc_post_env").write_text(
        f"QC_POST_ENV_FILE={home / 'a'}\nAI_POST_ENV_FILE={home / 'b'}\n"
    )

    config.load_env_file()

    assert config.env_file() == home / ".qc_post_env"
    assert "QC_POST_ENV_FILE" not in os.environ
    assert "AI_POST_ENV_FILE" not in os.environ


# ---------------------------------------------------------------------------
# Rule 3: the data folder
# ---------------------------------------------------------------------------


def test_data_dir_override_variables(monkeypatch, home, defaults):
    (home / "QuestCast").mkdir()
    (home / "XPosts").mkdir()

    monkeypatch.setenv("AI_POST_DATA_DIR", "/old/data")
    assert config.data_dir() == Path("/old/data")  # AI_POST_DATA_DIR exists today

    monkeypatch.setenv("QC_POST_DATA_DIR", "/new/data")
    assert config.data_dir() == Path("/new/data")
    assert config.legacy_notices() == [
        "questcast: AI_POST_DATA_DIR is ignored because QC_POST_DATA_DIR is set"
    ]


def test_data_dir_new_only(home, defaults):
    (home / "QuestCast").mkdir()

    assert config.data_dir() == home / "QuestCast"
    assert config.legacy_notices() == []


def test_data_dir_old_only(home, defaults):
    (home / "XPosts").mkdir()

    assert config.data_dir() == home / "XPosts"
    assert config.legacy_notices() == [
        "questcast: using ~/XPosts; move it with: mv ~/XPosts ~/QuestCast"
    ]


def test_data_dir_both_new_wins_and_old_is_untouched(home, defaults):
    (home / "QuestCast").mkdir()
    (home / "XPosts").mkdir()
    (home / "XPosts" / "history.json").write_text("[]")
    before = sorted(p.name for p in home.rglob("*"))

    assert config.data_dir() == home / "QuestCast"
    assert config.legacy_notices() == ["questcast: ~/XPosts is ignored because ~/QuestCast exists"]
    assert sorted(p.name for p in home.rglob("*")) == before


def test_data_dir_neither_defaults_to_the_new_name_without_creating_it(home, defaults):
    assert config.data_dir() == home / "QuestCast"
    assert config.legacy_notices() == []
    assert not (home / "QuestCast").exists()


# ---------------------------------------------------------------------------
# Rule 4: qc init
# ---------------------------------------------------------------------------


def tree(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def test_init_neither_folder_creates_questcast_with_mode_700(monkeypatch, home, defaults, capsys):
    run_cli(monkeypatch, "init")

    assert (home / "QuestCast" / "author_profile.md").read_bytes() == EXAMPLE
    assert (home / "QuestCast").stat().st_mode & 0o777 == 0o700
    assert not (home / "XPosts").exists()
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "~/.qc_post_env" in captured.out


def test_init_only_new_folder(monkeypatch, home, defaults, capsys):
    (home / "QuestCast").mkdir()

    run_cli(monkeypatch, "init")

    assert (home / "QuestCast" / "author_profile.md").exists()
    assert not (home / "XPosts").exists()
    assert capsys.readouterr().err == ""


def test_init_only_old_folder_with_profile_refuses_and_prints_the_move(
    monkeypatch, home, defaults, capsys
):
    (home / "XPosts").mkdir()
    (home / "XPosts" / "author_profile.md").write_text(PROFILE)
    before = tree(home)

    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, "init")

    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "using ~/XPosts; move it with: mv ~/XPosts ~/QuestCast" in err
    assert "already exists" in err
    assert (home / "XPosts" / "author_profile.md").read_text() == PROFILE
    assert tree(home) == before  # no QuestCast, no run.log, nothing moved


def test_init_only_old_folder_without_profile_writes_into_it(monkeypatch, home, defaults, capsys):
    (home / "XPosts").mkdir()

    run_cli(monkeypatch, "init")

    assert (home / "XPosts" / "author_profile.md").read_bytes() == EXAMPLE
    assert not (home / "QuestCast").exists()
    assert "mv ~/XPosts ~/QuestCast" in capsys.readouterr().err


def test_init_both_folders_uses_the_new_one_and_leaves_the_old_one(
    monkeypatch, home, defaults, capsys
):
    (home / "QuestCast").mkdir()
    (home / "XPosts").mkdir()
    (home / "XPosts" / "author_profile.md").write_text(PROFILE)

    run_cli(monkeypatch, "init")

    assert (home / "QuestCast" / "author_profile.md").read_bytes() == EXAMPLE
    assert (home / "XPosts" / "author_profile.md").read_text() == PROFILE
    assert tree(home / "XPosts") == ["author_profile.md"]
    assert "~/XPosts is ignored because ~/QuestCast exists" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Rule 5: notices
# ---------------------------------------------------------------------------


def test_shown_strips_control_characters_and_abbreviates_home(home):
    assert config.shown(home / "XPosts") == "~/XPosts"
    assert config.shown(home) == "~"
    dirty = config.shown(Path("/a/\x1b[31mb\nc\u2028d\u2029e\x85f"))
    assert not config.CONTROL_CHARS.search(dirty)
    assert dirty == "/a/ [31mb c d e f"


def test_notices_in_a_home_with_control_characters_are_clean(
    monkeypatch, tmp_path, defaults, capsys
):
    weird = tmp_path / "ho\x1b[31mme\nx"
    (weird / "XPosts").mkdir(parents=True)
    (weird / "XPosts" / "author_profile.md").write_text(PROFILE)
    monkeypatch.setenv("HOME", str(weird))

    run_cli(monkeypatch, "--list-topics")

    err = capsys.readouterr().err
    assert err.strip() == "questcast: using ~/XPosts; move it with: mv ~/XPosts ~/QuestCast"
    assert "\x1b" not in err


def test_a_run_prints_each_notice_once_and_leaks_nothing(
    monkeypatch, web, tmp_path, home, defaults, profile_file, capsys
):
    (home / "XPosts").mkdir()
    (home / "XPosts" / "author_profile.md").write_text(profile_file.read_text())
    (home / ".ai_post_env").write_text(
        f"export GROQ_API_KEY={SENTINEL_KEY}\nAI_POST_PROVIDER=groq\nAI_POST_SEARCH=native\n"
    )
    monkeypatch.setenv("AI_POST_TOKEN_BUDGET", "7000")
    web.add(GROQ_URL, completion(MODEL_OUTPUT))

    run_cli(monkeypatch, "--topic", "Cloud")

    captured = capsys.readouterr()
    assert [line for line in captured.err.splitlines() if line.startswith("questcast:")] == [
        "questcast: AI_POST_PROVIDER, AI_POST_SEARCH, AI_POST_TOKEN_BUDGET are deprecated; "
        "rename them to QC_POST_*. Old names stop working after the next release.",
        "questcast: using ~/.ai_post_env; rename it with: mv ~/.ai_post_env ~/.qc_post_env",
        "questcast: using ~/XPosts; move it with: mv ~/XPosts ~/QuestCast",
    ]
    data = home / "XPosts"
    files = {p.name: p.read_text() for p in data.iterdir() if p.is_file()}
    assert set(files) == {"author_profile.md", "history.json", "drafts.md", "run.log"}
    written = captured.out + captured.err + "".join(files.values())
    assert SENTINEL_KEY not in written
    for name in ("history.json", "drafts.md", "run.log"):
        assert "questcast:" not in files[name]
        assert "deprecated" not in files[name]
    assert json.loads(files["history.json"])[-1]["provider"] == "groq"
    assert not (home / "QuestCast").exists()
    assert (home / ".ai_post_env").read_text().count(SENTINEL_KEY) == 1  # not moved or edited


def test_no_notices_when_only_new_names_are_used(monkeypatch, home, defaults, profile_file, capsys):
    (home / "QuestCast").mkdir()
    (home / "QuestCast" / "author_profile.md").write_text(profile_file.read_text())
    (home / ".qc_post_env").write_text("QC_POST_SEARCH=native\n")

    run_cli(monkeypatch, "--list-topics")

    assert capsys.readouterr().err == ""
