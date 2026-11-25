# Changelog

All notable changes to this project are recorded here, newest first.

## Unreleased

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
