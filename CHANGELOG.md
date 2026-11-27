# Changelog

All notable changes to this project are recorded here, newest first.

## Unreleased

## 4.1.2

### Added

- PyPI publishing: publishing a GitHub release starts `pypi.yml`, which verifies the release's
  wheel and sdist attestations and, after the maintainer approves the `pypi` environment,
  uploads those same files with Trusted Publishing (no stored token). A manual run with a tag
  uploads to TestPyPI only.
- PyPI project page: project URLs (Homepage, Source, Changelog, Issues), keywords and
  classifiers; the README's images and LICENSE link are absolute so they show on PyPI.

### Fixed

- A 429 whose body says "try again in" followed by a very long digit string no longer raises
  `OverflowError` while the error is being formatted. `suggested_wait` returns no wait for a
  non-finite body value, and the daily-limit sentence leaves out the wait when it is not finite
  or is negative.

### Documentation

- README, iPhone (a-Shell): records the 26 Nov 2026 test of 4.1.1 (`--post-all` opens X, waits
  for Return, then opens LinkedIn) and says the Shortcut was tested on 4.0.0, not re-run on 4.1.1.

## 4.1.1

### Fixed

- iPhone (a-Shell): `--post-all`, and `--post` with `--post-linkedin`, opens X, then waits for
  Return before opening LinkedIn ("Press Return to open LinkedIn's post box (Ctrl-C to
  skip)."), because iOS drops a second open made while a-Shell is in the background. Ctrl-C or
  end of input skips LinkedIn and prints its link. With no terminal (the Shortcut), it opens X,
  prints the LinkedIn link and never says "Opened LinkedIn's post box." without opening it.
  Other platforms and single-site flags are unchanged.
- A daily-limit 429 (a body naming "tokens per day") now says "Groq's daily token limit is used
  up. Groq suggests waiting about N minutes (S s)." instead of "Wait a minute and re-run." and
  the tokens-per-minute hint. Other 429s keep their text. Provider error text is now stripped
  of control characters in every HTTP error message.
- Paired Markdown emphasis (`**text**`, `__text__`, `*text*`) is removed from both drafts before
  the length checks, the compose links, the screen and `drafts.md`, and the prompt asks for plain
  text. URLs, a lone `*`, bullets, hashtags and markers inside a word are left alone.

## 4.1.0

### Changed

- `--post` opens X's compose box with the X draft filled in, instead of posting through X's
  paid API. Nothing is posted until you click Post. If no browser opens, it prints the
  link to copy. New runs record `posted_x` false and `tweet_id` "", and the
  screen and `drafts.md` always say "X — draft".
- The screen no longer prints the compose links. After the drafts it prints one line saying
  they are in `drafts.md` and that `--post`, `--post-linkedin` or `--post-all` opens them.
  When a flag opens a box it prints `Opened X's compose box.` or `Opened LinkedIn's post
  box.`; when no browser opens it prints `No browser opened; to post on <site>, open this
  link:` and the full link on its own line, so it can be copied (a-Shell).
- `--post-linkedin` opens LinkedIn's post box with the LinkedIn draft filled in, instead of
  publishing through LinkedIn's API. Nothing is posted until you click Post. If no browser
  opens, it prints the link to copy. With `--post` as well, X opens first,
  then LinkedIn. New runs record `posted_linkedin` false, and the screen and `drafts.md`
  always say "LINKEDIN — draft".

### Added

- Every draft run writes `[Post on X](<link>)` into that run's `drafts.md` entry. The link is
  X's web intent URL with the draft percent-encoded.
- Every draft run writes `[Post on LinkedIn](<link>)` into that run's `drafts.md` entry
  under `## LinkedIn`. The link is
  `https://www.linkedin.com/feed/?shareActive=true&text=` plus the draft percent-encoded.
  LinkedIn doesn't document it, so LinkedIn could change it; if it opens an empty post box,
  the draft is on screen and in `drafts.md`.
- `--post-all` opens both boxes, X first, then LinkedIn; the same as `--post --post-linkedin`.

### Removed

- The tweepy route: `post_to_x`, `config.x_credentials` and the `X_API_KEY`, `X_API_SECRET`,
  `X_ACCESS_TOKEN` and `X_ACCESS_SECRET` settings. Old history entries keep their `posted_x`
  and `tweet_id` keys.
- The LinkedIn API route: `post_to_linkedin`, `questcast/publish.py` and the
  `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_AUTHOR_URN` and `LINKEDIN_API_VERSION` settings. Old
  history entries keep their `posted_linkedin` key.

### Documentation

- README: the iPhone (a-Shell) section now records a test of 4.0.0 on 25 Nov 2026: install, --list-topics, a native draft and the Home Screen Shortcut.

## 4.0.0

### Removed

- The `xgp` command. Use `qc`.
- Every `AI_POST_*` setting. Only `QC_POST_*` is read.
- The `~/XPosts` data folder and the `~/.ai_post_env` key file as fallbacks. Only `~/QuestCast` and
  `~/.qc_post_env` are read.
- The `~/.ai_post_venv` hints in the install messages.

### Changed

- **Breaking:** an old name now stops the run instead of being read. `qc` exits with status 1,
  before it reads the profile or writes anything (not even `run.log`), when an `AI_POST_*` setting
  is set in the shell or the env file (even with the `QC_POST_*` one also set), when `~/XPosts`
  exists and `~/QuestCast` doesn't, or when `~/.ai_post_env` exists and `~/.qc_post_env` doesn't.
  One message lists every problem, names and paths only, never values, with the fix for each. If
  both the old and the new folder (or key file) exist, the new one is used and nothing is said.
  `--help` still works. See "Upgrading to 4.0" in the README.
- The HTTP user agent is `QuestCast/4`.

### Fixed

- A failure writing `run.log` no longer raises a second error on top of the first: it is one line
  on stderr, and the original error still shows. If the data folder can't be created, `qc` says
  which folder, why, and that `QC_POST_DATA_DIR` moves it, with no traceback. A data folder that
  `qc` creates is mode 700; an existing one keeps its mode. (Found in a-Shell on iOS, where only
  `Documents` is writable.)
- The missing-key message no longer tells you to `echo` the key into the file. It gives the
  private-first steps: create the file with `umask 077`, then add the key in an editor.
- `qc` refuses to run while the profile still has the example's placeholders (or its unedited
  Beat), naming the profile and the sections to fill in. Before, the placeholders went to the
  provider ("Searching: (topic)", then a Groq 400).

### Documentation

- README: an "iPhone (a-Shell)" section with the setup tested on 25 Nov 2026, and a platforms line
  under Requirements.

## 3.1.1

### Fixed

- Runs on Python 3.13 (3.13 or later is now required, down from 3.14), so the wheel installs
  in a-Shell on iOS. 3.1.0 failed on import there with `SyntaxError: multiple exception types
  must be parenthesized`. Cause: ruff's `target-version` was `py314`, which allowed the
  Python 3.14-only form `except A, B:` (PEP 758) in `feeds.py` and `providers.py`. The target
  is now `py313`, a test keeps it equal to the minimum in `requires-python`, and CI runs the
  whole test suite on 3.13 as well as 3.14.

## 3.1.0

- Packaging: QuestCast is an installable package with a lockfile (`uv.lock`) and the `qc`
  command; `qc init` creates the data directory and an author profile to fill in. Install from
  a tagged release with `uv tool install` or `pipx` (see the README). Optional `anthropic` extra,
  pinned exactly; the default install stays standard library only.
- Security CI and the engineering baseline: `make check` (ruff, mypy, pytest with an 85% coverage
  floor), `make audit`, the required `check`, `gitleaks`, `semgrep`, `pip-audit` and `zizmor`
  jobs, daily pip-audit, Dependabot, OpenSSF Scorecard, Claude review, shared agent rules in
  `AGENTS.md` and a sandboxed `.claude/settings.json`, a pre-push gitleaks hook and `SECURITY.md`.
- Releases: pushing a `v*` tag builds the wheel and sdist, writes a CycloneDX SBOM of the default
  install's runtime dependencies, attests all three (build provenance) and opens a draft GitHub
  release with them attached. `CHANGELOG.md` supplies the release notes.
- Real-use fixes: one bounded wait and retry on rate limits (429), progress on stderr, a token
  budget for `--search rss`, clean provider error text, credentials never sent to another origin
  on a redirect, LinkedIn publishing through the shared opener, and a clear reason when a
  provider returns no text.
- The product is renamed QuestCast: package `questcast`, command `qc`, data folder `~/QuestCast`,
  key file `~/.qc_post_env` and `QC_POST_*` settings. The old names (`xgp`, `~/XPosts`,
  `~/.ai_post_env`, `AI_POST_*`) still work for this release, with a notice on stderr, and are
  removed in the next. See "Migrating from XGeneratePosts" in the README.
- The command line rejects abbreviated flags, so a prefix such as `--post-l` can no longer stand
  in for `--post-linkedin`.
