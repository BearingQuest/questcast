"""R75: paired Markdown emphasis is removed from both drafts."""

import sys
import webbrowser
from urllib.parse import quote

import pytest

from questcast import cli, config, providers
from questcast.fields import strip_emphasis
from tests.conftest import SENTINEL_KEY


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("**and**", "and"),
        ("this **and** that", "this and that"),
        ("__and__", "and"),
        ("this __and__ that", "this and that"),
        ("*really*", "really"),
        ("it is *really* good", "it is really good"),
        ("(*really*), **sure**.", "(really), sure."),
        ("**two words** and __more words__", "two words and more words"),
        ("first **a**\n\nsecond *b*", "first a\n\nsecond b"),
        ("**a *b* c**", "a b c"),
        # left alone
        ("5 * 3", "5 * 3"),
        ("5 * 3 * 2", "5 * 3 * 2"),
        ("2*3*4", "2*3*4"),
        ("a**b**c", "a**b**c"),
        ("snake__case__name", "snake__case__name"),
        ("* bullet one\n* bullet two", "* bullet one\n* bullet two"),
        ("#AI #cloud_native", "#AI #cloud_native"),
        ("a lone * star and ** pair", "a lone * star and ** pair"),
        ("** spaced **", "** spaced **"),
        ("https://a.example/x_y_z?q=*a*&r=__b__", "https://a.example/x_y_z?q=*a*&r=__b__"),
        ("see **this** https://a.example/__x__ *now*", "see this https://a.example/__x__ now"),
    ],
)
def test_strip_emphasis(text, expected):
    assert strip_emphasis(text) == expected


URL = "https://vendor.example/post_with_*stars*"
RAW = (
    f"===URL===\n{URL}\n===TITLE===\nA Real Release\n===SOURCE===\nVendor\n"
    "===TWEET===\nVendor **shipped** a *thing* #news\n"
    "===LINKEDIN===\nA **bold** take.\n\nWhat would you *ask* first? {pad}\n"
    "===WHY===\nw\n===END===\n"
)


CLEANED = "A bold take.\n\nWhat would you ask first? "
PAD = "x" * (config.MAX_LINKEDIN_TEXT - len(CLEANED))


@pytest.fixture
def run(monkeypatch, profile_file, capsys):
    """Run `--search native --post-all` with a model reply holding Markdown."""
    monkeypatch.setenv("GROQ_API_KEY", SENTINEL_KEY)

    def go(pad=""):
        text = RAW.format(pad=pad)
        monkeypatch.setattr(providers.GroqProvider, "generate", lambda self, prompt, **kw: text)
        monkeypatch.setattr(webbrowser, "open", lambda url, *a, **k: calls.append(url) or True)
        calls: list[str] = []
        argv = ["daily_post.py", "--topic", "Cloud", "--profile", str(profile_file)]
        monkeypatch.setattr(sys, "argv", [*argv, "--search", "native", "--post-all"])
        monkeypatch.setattr(cli, "platform_name", lambda: "linux")
        cli.main()
        return calls, capsys.readouterr()

    return go


def test_drafts_and_compose_links_carry_the_cleaned_text(run):
    calls, captured = run()
    tweet = f"Vendor shipped a thing #news\n{URL}"
    linkedin = f"A bold take.\n\nWhat would you ask first?\n\n{URL}"
    assert tweet in captured.out
    assert linkedin in captured.out
    assert "**" not in captured.out.split("LINKEDIN")[0].split("X \u2014 draft")[1]
    assert calls[0].endswith(quote(tweet, safe=""))
    assert calls[1].endswith(quote(linkedin, safe=""))
    saved = config.drafts_file().read_text()
    assert tweet in saved
    assert linkedin in saved
    assert "**bold**" not in saved


def test_length_at_the_ceiling_after_cleaning_is_not_warned(run):
    # The raw draft is 4 marker characters over the ceiling; the cleaned one is not.
    _, captured = run(PAD)
    assert "LinkedIn draft is" not in captured.err
    assert f"[{config.MAX_LINKEDIN_TEXT} characters]" in captured.out


def test_length_warning_uses_the_cleaned_length(run):
    _, captured = run(PAD + "xy")
    assert f"LinkedIn draft is {config.MAX_LINKEDIN_TEXT + 2} characters" in captured.err
