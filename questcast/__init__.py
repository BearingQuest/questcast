"""
QuestCast

Picks a technology topic, finds one noteworthy recent item on it, and drafts
two posts from that same source:

  * X/Twitter — short, link-forward, hashtagged.
  * LinkedIn  — longer, first-person point of view on why the item matters.

The topic is chosen at run time: pass --topic, or answer the numbered menu.
The menu comes from the '## Topics' section of your author profile if you
have one, otherwise from TOPIC_CATALOG below.

What makes the posts sound like YOU is an author profile file kept outside
this repo (default: ~/QuestCast/author_profile.md). `qc init` copies the
scaffold, author_profile.example.md in this package, there to fill in.

Default behavior is draft-only: both posts are printed and appended to
drafts.md for you to review and post yourself. Each run also prints a link that
opens X's compose box with the X draft filled in; --post opens it for you, and
nothing is posted until you click Post. --post-linkedin can publish to LinkedIn.

The model comes from one of three providers (--provider, default groq):

  * groq           — free tier; the standard library is enough.
  * openai-compat  — any OpenAI-compatible endpoint (Gemini, Cerebras, Ollama).
  * anthropic      — paid; needs the anthropic package.

Requirements:
    Python standard library only for groq and openai-compat.
    The 'anthropic' extra        (only for --provider anthropic)
    Installed qc, from the clone:  uv tool install --reinstall '.[anthropic]'
    The clone's venv:               ~/.qc_post_venv/bin/pip install -e '.[anthropic]'
    The pinned version is in pyproject.toml.

Credentials are read from ~/.qc_post_env — see README.md.
"""
