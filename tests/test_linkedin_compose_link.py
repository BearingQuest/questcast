"""R67 to R72: the "Post on LinkedIn" link, --post-linkedin and --post-all opening the
compose boxes, and no LinkedIn API path."""

import json
import re
import sys
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from questcast import cli, config, fields
from tests.conftest import SENTINEL_KEY

HOSTILE = [
    "plain draft\nhttps://vendor.example/post",
    "line one\nline \"two\" and 'three'\n\nhttps://vendor.example/a?b=1&c=2#frag #hashtag",
    "backtick ` dollar $HOME semicolon ; ampersand & hash # question ? space  tab\t",
    "naïve café — 日本語 🚀 \u2028 end",
    "100% sure %41 %",
    ("A 1,100-character line, with ? & # and é.\n\n" * 30)[: config.MAX_LINKEDIN_TEXT],
]
SAFE_LINK = re.compile(
    r"^https://www\.linkedin\.com/feed/\?shareActive=true&text=[A-Za-z0-9%._~-]*$"
)
ROOT = Path(__file__).resolve().parents[1]
POINTER = (
    "Compose links for X and LinkedIn are in drafts.md; --post, --post-linkedin "
    "or --post-all opens them."
)


def test_the_long_draft_is_1100_characters():
    assert len(HOSTILE[-1]) == 1100


@pytest.mark.parametrize("draft", HOSTILE)
def test_link_round_trips_the_exact_draft(draft):
    parts = urlsplit(fields.linkedin_compose_link(draft))
    assert (parts.scheme, parts.netloc, parts.path) == ("https", "www.linkedin.com", "/feed/")
    assert parse_qs(parts.query, keep_blank_values=True) == {
        "shareActive": ["true"],
        "text": [draft],
    }


@pytest.mark.parametrize("draft", HOSTILE)
def test_link_holds_only_url_safe_characters(draft):
    # webbrowser hands the URL to osascript on macOS; full encoding keeps it inert.
    assert SAFE_LINK.match(fields.linkedin_compose_link(draft))


@pytest.mark.parametrize("draft", HOSTILE)
def test_link_is_safe_inside_a_markdown_link(draft):
    # drafts.md holds it as [Post on LinkedIn](<link>): no bracket, parenthesis or whitespace.
    assert not re.search(r"[()\[\]\s]", fields.linkedin_compose_link(draft))


ITEM = {
    "url": "https://vendor.example/post?a=1&b=2",
    "title": "A Real Release",
    "source": "Vendor",
    "tweet": 'Vendor shipped "a thing" #news & more',
    "linkedin": "A longer take.\n\nWhat would you ask first? #security",
    "why": "It is substantive.",
}


@pytest.fixture
def draft_run(monkeypatch, profile_file):
    """Run cli.main() with the item fixed; returns (links, the browser calls)."""
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
        x_post, li_post = fields.compose_posts(ITEM)
        return fields.x_compose_link(x_post), fields.linkedin_compose_link(li_post), calls

    return run


def test_without_a_flag_the_screen_has_a_pointer_not_the_link(draft_run, capsys):
    _, link, calls = draft_run()
    out = capsys.readouterr().out
    _, li_post = fields.compose_posts(ITEM)
    assert li_post in out
    assert "LINKEDIN — draft" in out
    assert "PUBLISHED" not in out
    assert link not in out
    assert "Post on LinkedIn" not in out
    assert out.count(POINTER) == 1
    assert out.index(li_post) < out.index("Saved to") < out.index(POINTER)
    assert calls == []  # without a post flag nothing is opened


def test_drafts_md_holds_the_link_as_a_markdown_link(draft_run):
    _, link, _ = draft_run()
    _, li_post = fields.compose_posts(ITEM)
    drafts = config.drafts_file().read_text()
    assert f"## LinkedIn\n\n{li_post}\n\n[Post on LinkedIn]({link})\n" in drafts
    assert "(POSTED)" not in drafts


def test_the_draft_text_is_unchanged_and_the_link_adds_no_other_parameter(draft_run):
    _, link, _ = draft_run()
    _, li_post = fields.compose_posts(ITEM)
    assert parse_qs(urlsplit(link).query) == {"shareActive": ["true"], "text": [li_post]}
    assert li_post == f"{ITEM['linkedin']}\n\n{ITEM['url']}"


def test_post_linkedin_opens_the_link_once_after_the_drafts_are_saved(draft_run, capsys):
    _, link, calls = draft_run("--post-linkedin")
    out = capsys.readouterr().out
    assert calls == [link]
    assert "[Post on LinkedIn](" in config.drafts_file().read_text()
    assert out.count("Opened LinkedIn's post box.\n") == 1
    assert link not in out  # the link is printed only when no browser opens
    assert POINTER not in out
    assert "No browser opened" not in out


def test_post_and_post_linkedin_open_x_then_linkedin(draft_run):
    x_link, li_link, calls = draft_run("--post", "--post-linkedin")
    assert calls == [x_link, li_link]


@pytest.mark.parametrize(
    "flags",
    [("--post-all",), ("--post-all", "--post", "--post-linkedin")],
)
def test_post_all_opens_x_then_linkedin_once_each(draft_run, flags):
    x_link, li_link, calls = draft_run(*flags)
    assert calls == [x_link, li_link]


@pytest.mark.parametrize("failure", [False, webbrowser.Error("no runnable browser")])
def test_post_linkedin_without_a_browser_prints_one_line_and_exits_0(draft_run, capsys, failure):
    _, link, calls = draft_run("--post-linkedin", opened=failure)  # a raise would fail the test
    out = capsys.readouterr().out
    assert calls == [link]
    assert out.count("No browser opened") == 1
    assert f"No browser opened; to post on LinkedIn, open this link:\n{link}\n" in out
    assert "Opened LinkedIn's post box." not in out
    assert "to post on X" not in out


def test_post_all_without_a_browser_prints_each_link_for_its_site(draft_run, capsys):
    x_link, li_link, _ = draft_run("--post-all", opened=False)
    out = capsys.readouterr().out
    assert f"No browser opened; to post on X, open this link:\n{x_link}\n" in out
    assert f"No browser opened; to post on LinkedIn, open this link:\n{li_link}\n" in out


def test_post_all_prints_one_opened_line_per_box(draft_run, capsys):
    x_link, li_link, _ = draft_run("--post-all")
    out = capsys.readouterr().out
    assert out.index("Opened X's compose box.") < out.index("Opened LinkedIn's post box.")
    assert x_link not in out and li_link not in out


def test_history_records_no_linkedin_post(draft_run):
    draft_run("--post-linkedin")
    entry = json.loads(config.history_file().read_text())[-1]
    assert entry["posted_linkedin"] is False


def test_no_module_references_the_linkedin_api():
    assert not (ROOT / "questcast" / "publish.py").exists()
    for path in (ROOT / "questcast").glob("*.py"):
        assert "api.linkedin.com" not in path.read_text(), path.name
