"""R62 to R65: the "Post on X" link, --post opening X's compose box, and no X API path."""

import importlib
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


def test_link_is_on_stdout_after_the_draft_and_in_drafts_md(draft_run, capsys):
    link, calls = draft_run()
    out = capsys.readouterr().out
    x_post, _ = fields.compose_posts(ITEM)
    assert f"{x_post}\nPost on X: {link}\n" in out
    assert out.count("Post on X: ") == 1
    assert "X — draft" in out
    assert f"## X\n\n{x_post}\n\nPost on X: {link}\n" in config.drafts_file().read_text()
    assert calls == []  # without --post nothing is opened


def test_the_draft_text_is_unchanged_and_the_link_adds_no_url_parameter(draft_run):
    link, _ = draft_run()
    x_post, _ = fields.compose_posts(ITEM)
    query = parse_qs(urlsplit(link).query)
    assert query == {"text": [x_post]}
    assert x_post.endswith(ITEM["url"])


def test_post_opens_the_link_once_after_the_drafts_are_saved(draft_run, capsys):
    link, calls = draft_run("--post")
    assert calls == [link]
    assert "Post on X: " in config.drafts_file().read_text()
    assert "No browser opened" not in capsys.readouterr().out


@pytest.mark.parametrize("failure", [False, webbrowser.Error("no runnable browser")])
def test_post_without_a_browser_prints_one_line_and_exits_0(draft_run, capsys, failure):
    link, calls = draft_run("--post", opened=failure)  # main() raising would fail the test
    out = capsys.readouterr().out
    assert calls == [link]
    assert out.count("No browser opened") == 1
    assert f"Post on X: {link}" in out


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
    assert not hasattr(importlib.import_module("questcast.publish"), "post_to_x")
