"""qc refuses a profile that still holds the example's text, before any
provider is built or called."""

import sys

import pytest

from questcast import cli, storage
from questcast.author_profile import parse_profile, unfilled_sections

EXAMPLE_TEXT = storage.example_profile_text()


def parsed(text):
    return parse_profile(text, "p.md")


def example():
    return parsed(EXAMPLE_TEXT)


def filled(**overrides):
    sections = {
        "topics": "- Cloud",
        "beat": "Practitioners.",
        "voice": "Plain.",
        "experience": "- Cut the build from 40 to 12 minutes.",
        "hashtags": "#Cloud #SRE",
    }
    sections.update(overrides)
    return {name: body for name, body in sections.items() if body is not None}


def run_with(monkeypatch, profile_text, tmp_path, extra=()):
    path = tmp_path / "p.md"
    path.write_text(profile_text)

    def no_provider(name):
        raise AssertionError("a provider was built for an unedited profile")

    monkeypatch.setattr(cli, "make_provider", no_provider)
    monkeypatch.setattr(sys, "argv", ["qc", "--profile", str(path), *extra])
    return path


def test_unedited_example_is_refused_naming_path_and_sections(monkeypatch, tmp_path, capsys):
    path = run_with(monkeypatch, EXAMPLE_TEXT, tmp_path)

    with pytest.raises(SystemExit) as exc:
        cli.main()

    message = str(exc.value.code)
    assert str(path) in message
    for section in ("## Topics", "## Beat", "## Voice", "## Experience", "## Hashtags"):
        assert section in message
    assert "Traceback" not in capsys.readouterr().err
    assert "FAILED" in (tmp_path / "run.log").read_text()


def test_filled_profile_is_not_refused():
    assert unfilled_sections(filled(), example()) == []


@pytest.mark.parametrize(
    ("section", "line"),
    [
        ("topics", "- (topic)"),
        ("experience", "- (achievement)"),
        ("voice", "- (2-4 real positions, including anything where you disagree with the"),
        ("hashtags", "#YourTag #YourTag #YourTag"),
    ],
)
def test_each_example_placeholder_line_is_flagged_on_its_own(section, line):
    profile = filled(**{section: f"Real text first.\n{line}"})

    assert unfilled_sections(profile, example()) == [section]


def test_beat_equal_to_the_example_is_flagged():
    assert unfilled_sections(filled(beat=example()["beat"]), example()) == ["beat"]


def test_a_real_line_starting_with_a_parenthesis_is_not_flagged():
    profile = filled(experience="- (2019) Led the move to Kubernetes.\n- (Rare) but real.")

    assert unfilled_sections(profile, example()) == []


def test_unchanged_never_section_is_allowed():
    assert unfilled_sections(filled(never=example()["never"]), example()) == []


def test_list_topics_still_works_on_the_example(monkeypatch, tmp_path, capsys):
    run_with(monkeypatch, EXAMPLE_TEXT, tmp_path, extra=("--list-topics",))

    cli.main()

    assert "(topic)" in capsys.readouterr().out
