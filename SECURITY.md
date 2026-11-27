# Security policy

## Reporting a vulnerability

Please report security issues privately through GitHub: on the repository's
**Security** tab, choose **Report a vulnerability**. Don't open a public
issue for a security problem.

Include what you found, the steps to reproduce it, and the commit you
tested. This is a one-person project, so replies may take a few days.

## Scope

QuestCast runs locally from the command line and has no hosted service.
Issues of particular interest:
- key handling: API keys and tokens are read from `~/.qc_post_env` and the
  environment (`questcast/config.py`) and must never be printed, including in error messages;
- what the author profile and topic send to the AI provider
  (`questcast/prompt.py`, `questcast/providers.py`);
- fetching feeds and following redirects (`questcast/net.py`,
  `questcast/feeds.py`), including the refusal to follow an HTTPS
  redirect to plain HTTP;
- the draft-only default: nothing is posted, and neither X's compose box nor LinkedIn's
  post box is opened, without an explicit `--post`, `--post-linkedin` or `--post-all`
  flag, and QuestCast never posts itself: you click Post;
- `qc init`: the profile it creates in `~/QuestCast` gets file mode 600, and an
  existing profile is never overwritten.

## Supported versions

Only the latest release is supported (4.x today). Security fixes land on
`master` and ship in the next release, which is what users install.

## Releases and PyPI

Pushing a `v*` tag makes `release.yml` build the wheel and the sdist and open a draft GitHub
release with build-provenance attestations. Publishing that release starts `pypi.yml`, which
downloads the wheel and the sdist, verifies both attestations against `release.yml`, and
then waits for the maintainer's approval of the `pypi` environment before uploading the same
files to PyPI. Uploads use PyPI Trusted Publishing (OIDC): no PyPI token is stored anywhere.
A manual run of `pypi.yml` with a tag uploads to TestPyPI only, behind the `testpypi`
environment.
