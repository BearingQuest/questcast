"""R73: on iOS, --post-all opens X, then waits for Return before LinkedIn."""

import builtins
import sys
import webbrowser

import pytest

from questcast import cli, fields
from tests.conftest import SENTINEL_KEY

ITEM = {
    "url": "https://vendor.example/post",
    "title": "A Real Release",
    "source": "Vendor",
    "tweet": "Vendor shipped a thing #news",
    "linkedin": "A longer take.\n\nWhat would you ask first?",
    "why": "It is substantive.",
}
PROMPT = "Press Return to open LinkedIn's post box (Ctrl-C to skip)."


@pytest.fixture
def run(monkeypatch, profile_file, capsys):
    """Run cli.main(); returns (browser calls, stdout)."""
    monkeypatch.setenv("GROQ_API_KEY", SENTINEL_KEY)
    monkeypatch.setattr(cli, "generate_item", lambda *args, **kwargs: dict(ITEM))

    def go(*flags, platform="ios", tty=True, answer=None):
        calls = []
        monkeypatch.setattr(webbrowser, "open", lambda url, *a, **k: calls.append(url) or True)
        monkeypatch.setattr(cli, "platform_name", lambda: platform)
        monkeypatch.setattr(sys.stdin, "isatty", lambda: tty)

        def fake_input(*args):
            if isinstance(answer, BaseException):
                raise answer
            return ""

        monkeypatch.setattr(builtins, "input", fake_input)
        argv = ["daily_post.py", "--topic", "Cloud", "--profile", str(profile_file), *flags]
        monkeypatch.setattr(sys, "argv", argv)
        cli.main()
        return calls, capsys.readouterr().out

    return go


def links():
    x_post, li_post = fields.compose_posts(ITEM)
    return fields.x_compose_link(x_post), fields.linkedin_compose_link(li_post)


def test_ios_tty_opens_x_prompts_then_opens_linkedin(run):
    calls, out = run("--post-all")
    assert calls == list(links())
    assert PROMPT in out
    assert out.index("Opened X's compose box.") < out.index(PROMPT)
    assert "Opened LinkedIn's post box." in out


@pytest.mark.parametrize("answer", [EOFError(), KeyboardInterrupt()])
def test_ios_skip_opens_x_only_and_prints_the_link(run, answer):
    calls, out = run("--post-all", answer=answer)
    x_link, li_link = links()
    assert calls == [x_link]
    assert f"No browser opened; to post on LinkedIn, open this link:\n{li_link}\n" in out
    assert "Opened LinkedIn's post box." not in out


def test_ios_without_a_tty_opens_x_only_and_prints_the_link(run):
    calls, out = run("--post-all", tty=False)
    x_link, li_link = links()
    assert calls == [x_link]
    assert PROMPT not in out
    assert f"No browser opened; to post on LinkedIn, open this link:\n{li_link}\n" in out
    assert "Opened LinkedIn's post box." not in out


def test_post_with_post_linkedin_behaves_like_post_all_on_ios(run):
    calls, out = run("--post", "--post-linkedin")
    assert calls == list(links())
    assert PROMPT in out


@pytest.mark.parametrize("flag", ["--post", "--post-linkedin"])
def test_single_site_flag_on_ios_never_prompts(run, flag):
    calls, out = run(flag)
    assert len(calls) == 1
    assert PROMPT not in out


def test_other_platforms_open_both_without_a_prompt(run):
    calls, out = run("--post-all", platform="darwin")
    assert calls == list(links())
    assert PROMPT not in out
