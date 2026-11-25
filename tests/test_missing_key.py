"""The missing-key message makes the key file private first and has the key
typed in an editor, never on a command line."""

import pytest

from questcast import config
from questcast.providers import AnthropicProvider, GroqProvider


@pytest.mark.parametrize(
    ("provider", "key_var"),
    [(GroqProvider, "GROQ_API_KEY"), (AnthropicProvider, "ANTHROPIC_API_KEY")],
)
def test_message_gives_the_private_first_steps(provider, key_var):
    with pytest.raises(SystemExit) as exc:
        provider().require_credentials()

    message = str(exc.value.code)
    assert str(config.env_file()) in message
    assert "umask 077" in message
    assert "editor" in message
    assert f"{key_var}=..." in message
    assert "echo" not in message
    assert "chmod" not in message
    assert "export" not in message
