"""DOC-06: the README environment table lists every variable the code reads, with its real
default, and no variable the code doesn't read.

Names are found in the code by AST, so a variable added to questcast/ without a README row
fails here. Defaults are computed by calling the config accessors in a clean environment.
"""

import ast
import re
from pathlib import Path

import pytest

from questcast import config

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PACKAGE = ROOT / "questcast"

PREFIXED = r"(?:QC|AI)_POST_[A-Z0-9_]+"
CREDENTIAL_OR_PROVIDER = (
    r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*"
    r"_(?:API_KEY|API_SECRET|ACCESS_TOKEN|ACCESS_SECRET|AUTHOR_URN|API_VERSION|MODEL|BASE_URL)"
)
ENV_NAME = re.compile(f"{PREFIXED}|{CREDENTIAL_OR_PROVIDER}")
ROW = re.compile(r"^\|\s*`([A-Z][A-Z0-9_]+)`\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$")

CREDENTIALS_WITH_NO_DEFAULT = (
    "X_API_KEY",
    "X_API_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_SECRET",
    "LINKEDIN_ACCESS_TOKEN",
    "LINKEDIN_AUTHOR_URN",
    "GROQ_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_COMPAT_API_KEY",
    "OPENAI_COMPAT_BASE_URL",
    "OPENAI_COMPAT_MODEL",
)


def readme_table() -> dict[str, str]:
    """{variable: default cell} for every row of the README whose first cell is a variable."""
    rows = {}
    for line in README.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match and ENV_NAME.fullmatch(match.group(1)):
            rows[match.group(1)] = match.group(2)
    return rows


def names_in_code() -> set[str]:
    """Every variable the package names: string constants that look like one, plus the
    QC_POST_ and AI_POST_ names that config builds from SETTING_NAMES."""
    found = {
        f"{prefix}{name}"
        for name in config.SETTING_NAMES
        for prefix in (config.NEW_PREFIX, config.OLD_PREFIX)
    }
    for path in sorted(PACKAGE.glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and ENV_NAME.fullmatch(node.value)
            ):
                found.add(node.value)
    return found


def first_token(cell: str) -> str:
    """The first backticked piece of a default cell, or the whole cell."""
    match = re.match(r"`([^`]*)`", cell)
    return match.group(1) if match else cell


def same_number(cell: str, expected: float) -> bool:
    try:
        return float(first_token(cell)) == expected
    except ValueError:
        return False


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """No variable the code reads is set, and HOME is an empty folder."""
    for name in names_in_code():
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))


def test_the_table_is_still_parsed():
    # A change of format must not leave the guard with nothing to check.
    assert len(readme_table()) >= 30


def test_every_variable_the_code_reads_is_in_the_readme_table():
    missing = sorted(names_in_code() - readme_table().keys())
    assert not missing, f"the README environment table is missing: {missing}"


def test_no_readme_row_names_a_variable_the_code_lacks():
    stale = sorted(readme_table().keys() - names_in_code())
    assert not stale, f"the README environment table lists variables the code never reads: {stale}"


def test_readme_defaults_match_the_code(clean_env):
    table = readme_table()
    wrong = {}

    def expect(name: str, ok: bool) -> None:
        if not ok:
            wrong[name] = table[name]

    expect("QC_POST_PROVIDER", first_token(table["QC_POST_PROVIDER"]) == config.DEFAULT_PROVIDER)
    search = table["QC_POST_SEARCH"]
    expect("QC_POST_SEARCH", all(f"`{source}`" in search for source in config.SEARCH_SOURCES))
    expect("QC_POST_PROVIDER_TIMEOUT", same_number(table["QC_POST_PROVIDER_TIMEOUT"], 120.0))
    assert config.provider_timeout() == 120.0
    expect(
        "QC_POST_RSS_PER_FEED", same_number(table["QC_POST_RSS_PER_FEED"], config.rss_per_feed())
    )
    expect(
        "QC_POST_RSS_MAX_ENTRIES",
        same_number(table["QC_POST_RSS_MAX_ENTRIES"], config.rss_max_entries()),
    )
    expect(
        "QC_POST_TOKEN_BUDGET", same_number(table["QC_POST_TOKEN_BUDGET"], config.token_budget())
    )
    expect(
        "QC_POST_RATE_LIMIT_WAIT",
        same_number(table["QC_POST_RATE_LIMIT_WAIT"], config.rate_limit_wait()),
    )
    expect(
        "QC_POST_DATA_DIR",
        first_token(table["QC_POST_DATA_DIR"]) == config.shown(config.data_dir()),
    )
    expect(
        "QC_POST_ENV_FILE",
        first_token(table["QC_POST_ENV_FILE"]) == config.shown(config.env_file()),
    )
    assert config.groq_model() == ""  # unset: the provider falls back to the default model
    expect("GROQ_MODEL", first_token(table["GROQ_MODEL"]) == config.GROQ_DEFAULT_MODEL)
    expect(
        "LINKEDIN_API_VERSION",
        first_token(table["LINKEDIN_API_VERSION"]) == config.linkedin_api_version(),
    )
    for name in CREDENTIALS_WITH_NO_DEFAULT:
        expect(name, table[name] == "none")
    # The code gives each of these no value when it is unset.
    assert not any(config.x_credentials().values())
    assert not config.linkedin_access_token()
    assert not config.linkedin_author_urn()
    assert not config.anthropic_api_key()
    assert not config.api_key("GROQ_API_KEY")
    assert not config.api_key("OPENAI_COMPAT_API_KEY")
    assert not config.openai_compat_base_url()
    assert not config.openai_compat_model()
    assert not wrong, f"README default differs from the code: {wrong}"


def test_every_variable_has_a_default_checked_here_or_is_a_legacy_name():
    checked = {
        "QC_POST_PROVIDER",
        "QC_POST_SEARCH",
        "QC_POST_PROVIDER_TIMEOUT",
        "QC_POST_RSS_PER_FEED",
        "QC_POST_RSS_MAX_ENTRIES",
        "QC_POST_TOKEN_BUDGET",
        "QC_POST_RATE_LIMIT_WAIT",
        "QC_POST_DATA_DIR",
        "QC_POST_ENV_FILE",
        "GROQ_MODEL",
        "LINKEDIN_API_VERSION",
        *CREDENTIALS_WITH_NO_DEFAULT,
    }
    unchecked = sorted(
        name for name in names_in_code() if name not in checked and not name.startswith("AI_POST_")
    )
    assert not unchecked, (
        f"add the default of these to test_readme_defaults_match_the_code: {unchecked}"
    )


def test_each_legacy_name_points_at_its_new_name():
    table = readme_table()
    for name in config.SETTING_NAMES:
        old, new = config.OLD_PREFIX + name, config.NEW_PREFIX + name
        assert f"`{new}`" in table[old], f"{old} should name {new} in its default cell"
