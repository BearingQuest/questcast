# Changelog

All notable changes to this project are recorded here, newest first.

## Unreleased

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
