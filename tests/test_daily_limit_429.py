"""R74: a daily-limit 429 says so, with Groq's wait in minutes; other 429s keep their text."""

import json

import pytest

from questcast import providers
from tests.conftest import SENTINEL_KEY

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
TPD = (
    "Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01fake` "
    "service tier `on_demand` on tokens per day (TPD): Limit 200000, Used 199000, "
    "Requested 6153. Please try again in 31m7.2s."
)
TPM = (
    "Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01fake` "
    "service tier `on_demand` on tokens per minute (TPM): Limit 8000, Used 5473, "
    "Requested 6153. Please try again in 27.195s."
)


@pytest.fixture
def groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", SENTINEL_KEY)
    # A wait over the limit is never retried, so each call is one 429.
    monkeypatch.setenv("QC_POST_RATE_LIMIT_WAIT", "0")
    return providers.GroqProvider()


def message_for(web, groq, text, retry_after=None, native_search=True):
    body = json.dumps({"error": {"message": text, "type": "tokens"}}).encode()
    headers = {"retry-after": retry_after} if retry_after else {}
    web.add(GROQ_URL, body, status=429, headers=headers)
    with pytest.raises(SystemExit) as exc:
        groq.generate("prompt", native_search=native_search)
    return exc.value.code


def test_tpd_429_names_the_daily_limit_and_the_wait(web, groq):
    out = message_for(web, groq, TPD, "1867")
    assert "Groq's daily token limit is used up." in out
    assert "Groq suggests waiting about 32 minutes (1867 s)." in out
    assert "Wait a minute" not in out
    assert "tokens-per-minute" not in out
    assert "Nothing was saved" in out


def test_tpd_429_over_the_wait_limit_keeps_the_wait_line(web, monkeypatch, groq):
    monkeypatch.setenv("QC_POST_RATE_LIMIT_WAIT", "60")
    out = message_for(web, groq, TPD, "1867")
    assert "Groq asked for 1867 s, longer than QC_POST_RATE_LIMIT_WAIT (60)" in out


@pytest.mark.parametrize(
    ("seconds", "words"),
    [
        ("60", "about 1 minute (60 s)"),
        ("1", "about 1 minute (1 s)"),
        ("61", "about 2 minutes (61 s)"),
    ],
)
def test_minutes_round_up_and_singular(web, groq, seconds, words):
    out = message_for(web, groq, TPD, seconds)
    assert f"suggests waiting {words}." in out
    assert "1 minutes" not in out


def test_tpd_429_without_a_wait_just_says_it_is_used_up(web, groq):
    out = message_for(web, groq, TPD)
    assert "Groq's daily token limit is used up." in out
    assert "suggests waiting" not in out


def test_tpd_429_with_an_overlong_wait_just_says_it_is_used_up(web, groq):
    text = TPD.replace("try again in 31m7.2s.", "try again in " + "9" * 400 + "s.")
    out = message_for(web, groq, text)
    assert "Groq's daily token limit is used up." in out
    assert "suggests waiting" not in out


def test_suggested_wait_ignores_a_non_finite_body_value():
    assert providers.suggested_wait({}, "try again in " + "9" * 400 + "s") is None


@pytest.mark.parametrize("seconds", [float("inf"), float("nan"), -5.0])
def test_daily_limit_sentence_ignores_a_bad_wait(seconds):
    assert providers.daily_limit_sentence("Groq", seconds) == "Groq's daily token limit is used up."


def test_tpm_429_keeps_todays_text(web, groq):
    out = message_for(web, groq, TPM, "27")
    assert "Wait a minute and re-run. groq suggests waiting 27 seconds." in out
    assert "tokens-per-minute limit, --search rss sends a smaller request." in out
    assert "daily token limit" not in out


def test_unclassified_429_keeps_todays_text(web, groq):
    out = message_for(web, groq, "Slow down", "5")
    assert "Wait a minute and re-run. groq suggests waiting 5 seconds." in out


@pytest.mark.parametrize("status", [403, 404, 413, 429])
def test_control_characters_in_provider_text_are_not_printed(web, groq, status):
    body = json.dumps({"error": {"message": "bad\x1b[2J thing\r\nnext", "type": "x"}}).encode()
    web.add(GROQ_URL, body, status=status)
    with pytest.raises(SystemExit) as exc:
        groq.generate("prompt")
    assert "\x1b" not in exc.value.code
    assert "\r" not in exc.value.code
    assert "bad" in exc.value.code
