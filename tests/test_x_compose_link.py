"""R62 to R65, R72: the "Post on X" link, --post opening X's compose box, and no X API path."""

import importlib.util
import json
import re
import sys
import webbrowser
from urllib.parse import parse_qs, urlsplit

import pytest

from questcast import cli, config, fields
from tests.conftest import SENTINEL_KEY

HOSTILE = [
    "plain draft\nhttps://vendor.example/post",
    "line one\nline \"two\" and 'three'\n\nhttps://vendor.example/a?b=1&c=2#frag",
    "backtick ` dollar $HOME semicolon ; ampersand & hash # question ? space  tab\t",
    "naïve café — 日本語 🚀 \u2028 end",
    "100% sure %41 %",
]
SAFE_LINK = re.compile(r"^https://x\.com/intent/tweet\?text=[A-Za-z0-9%._~-]*$")
POINTER = (
    "Compose links for X and LinkedIn are in drafts.md; --post, --post-linkedin "
    "or --post-all opens them."
)


@pytest.mark.parametrize("draft", HOSTILE)
def test_link_round_trips_the_exact_draft(draft):
    link = fields.x_compose_link(draft)
    parts = urlsplit(link)
    assert (parts.scheme, parts.netloc, parts.path) == ("https", "x.com", "/intent/tweet")
    assert parse_qs(parts.query, keep_blank_values=True) == {"text": [draft]}


@pytest.mark.parametrize("draft", HOSTILE)
def test_link_holds_only_url_safe_characters(draft):
    # webbrowser hands the URL to osascript on macOS; full encoding keeps it inert.
    assert SAFE_LINK.match(fields.x_compose_link(draft))


@pytest.mark.parametrize("draft", HOSTILE)
def test_link_is_safe_inside_a_markdown_link(draft):
    # drafts.md holds it as [Post on X](<link>): no bracket, parenthesis or whitespace.
    assert not re.search(r"[()\[\]\s]", fields.x_compose_link(draft))


ITEM = {
    "url": "https://vendor.example/post?a=1&b=2",
    "title": "A Real Release",
    "source": "Vendor",
    "tweet": 'Vendor shipped "a thing" #news & more',
    "linkedin": "A longer take.\n\nWhat would you ask first?",
    "why": "It is substantive.",
}


@pytest.fixture
def draft_run(monkeypatch, profile_file):
    """Run cli.main() with the item fixed; returns (link, the browser calls)."""
    monkeypatch.setenv("GROQ_API_KEY", SENTINEL_KEY)
    monkeypatch.setattr(cli, "generate_item", lambda *args, **kwargs: dict(ITEM))
    calls = []

    def run(*flags, opened=True):
        def fake_open(url, *args, **kwargs):
            calls.append(url)
            if isinstance(opened, Exception):
                raise opened
            return opened

        monkeypatch.setattr(webbrowser, "open", fake_open)
        argv = ["daily_post.py", "--topic", "Cloud", "--profile", str(profile_file), *flags]
        monkeypatch.setattr(sys, "argv", argv)
        cli.main()
        x_post, _ = fields.compose_posts(ITEM)
        return fields.x_compose_link(x_post), calls

    return run


def test_without_a_flag_the_screen_has_a_pointer_not_the_link(draft_run, capsys):
    link, calls = draft_run()
    out = capsys.readouterr().out
    x_post, _ = fields.compose_posts(ITEM)
    assert x_post in out
    assert "X — draft" in out
    assert link not in out
    assert "Post on X" not in out
    assert out.count(POINTER) == 1
    assert out.index("Saved to") < out.index(POINTER)  # after the LinkedIn draft and Saved to
    assert calls == []  # without --post nothing is opened


def test_drafts_md_holds_the_link_as_a_markdown_link(draft_run):
    link, _ = draft_run()
    x_post, _ = fields.compose_posts(ITEM)
    assert f"## X\n\n{x_post}\n\n[Post on X]({link})\n" in config.drafts_file().read_text()


def test_the_draft_text_is_unchanged_and_the_link_adds_no_url_parameter(draft_run):
    link, _ = draft_run()
    x_post, _ = fields.compose_posts(ITEM)
    query = parse_qs(urlsplit(link).query)
    assert query == {"text": [x_post]}
    assert x_post.endswith(ITEM["url"])


def test_post_opens_the_link_once_after_the_drafts_are_saved(draft_run, capsys):
    link, calls = draft_run("--post")
    out = capsys.readouterr().out
    assert calls == [link]
    assert "[Post on X](" in config.drafts_file().read_text()
    assert out.count("Opened X's compose box.\n") == 1
    assert link not in out  # the link is printed only when no browser opens
    assert POINTER not in out
    assert "No browser opened" not in out


@pytest.mark.parametrize("failure", [False, webbrowser.Error("no runnable browser")])
def test_post_without_a_browser_prints_one_line_and_exits_0(draft_run, capsys, failure):
    link, calls = draft_run("--post", opened=failure)  # main() raising would fail the test
    out = capsys.readouterr().out
    assert calls == [link]
    assert out.count("No browser opened") == 1
    assert f"No browser opened; to post on X, open this link:\n{link}\n" in out
    assert "Opened X's compose box." not in out


def test_history_records_no_post(draft_run):
    draft_run("--post")
    entry = json.loads(config.history_file().read_text())[-1]
    assert entry["posted_x"] is False
    assert entry["tweet_id"] == ""


def test_no_run_imports_tweepy_and_config_has_no_x_credentials(draft_run):
    sys.modules.pop("tweepy", None)
    draft_run("--post")
    assert "tweepy" not in sys.modules
    assert not hasattr(config, "x_credentials")
    assert importlib.util.find_spec("questcast.publish") is None
