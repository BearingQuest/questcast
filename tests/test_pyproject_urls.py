"""R77, R78: pyproject.toml gives PyPI's project page its four links."""

import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"
REPO_URL = "https://github.com/BearingQuest/questcast"


def test_project_urls_has_the_four_keys_pointing_at_this_repository() -> None:
    urls = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["urls"]
    assert set(urls) == {"Homepage", "Source", "Changelog", "Issues"}
    for name, url in urls.items():
        assert url.startswith(REPO_URL), (name, url)


def test_classifiers_name_no_development_status_and_no_license() -> None:
    # The SPDX `license` field covers the license; PEP 639 deprecates the classifier beside it.
    classifiers = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["classifiers"]
    assert not [c for c in classifiers if c.startswith(("Development Status", "License ::"))]
    assert "Programming Language :: Python :: 3.13" in classifiers
    assert "Programming Language :: Python :: 3.14" in classifiers
