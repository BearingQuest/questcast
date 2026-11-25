"""The author profile: its sections, and the topic menu it defines. No I/O."""

import re
from pathlib import Path

# Fallback topic menu. Override it with a '## Topics' section in your profile —
# one topic per line, optionally "Label — extra scoping detail".
TOPIC_CATALOG = [
    "AI and machine learning in the enterprise",
    "Cybersecurity and threat defense",
    "Cloud infrastructure and architecture",
    "Platform engineering and developer experience",
    "Site reliability, observability, and incident response",
    "DevOps, CI/CD, and release engineering",
    "Kubernetes and container platforms",
    "Identity and access management",
    "Data engineering and analytics platforms",
    "FinOps and cloud cost management",
    "Governance, risk, and compliance automation",
    "Agentic AI and workflow automation",
    "Networking, edge, and content delivery",
    "Engineering leadership and team practices",
]

# Profile sections. "required" ones must be present and non-empty.
PROFILE_SECTIONS = {
    "beat": True,  # audience, exclusions, what counts as a good find
    "voice": True,  # how the author thinks and sounds
    "topics": False,  # menu of technology areas to choose from
    "experience": False,  # verified things the author may reference
    "never": False,  # hard rules
    "hashtags": False,  # preferred tag pool
    "feeds": False,  # RSS/Atom feed URLs, used only with --search rss
}


def parse_profile(text: str, path: Path) -> dict[str, str]:
    """Parse the author profile into {section_name: body}.

    Sections are '## Heading' blocks. Heading names are matched
    case-insensitively against PROFILE_SECTIONS; unknown sections are ignored,
    so you can keep notes to yourself in the file. `path` is only named in
    the error message.
    """
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current = heading.group(1).strip().lower()
            sections[current] = []
        elif current:
            sections[current].append(line)

    parsed = {k: "\n".join(v).strip() for k, v in sections.items()}
    missing = [
        name for name, required in PROFILE_SECTIONS.items() if required and not parsed.get(name)
    ]
    if missing:
        raise SystemExit(
            f"{path} is missing required section(s): "
            + ", ".join(f"## {m.title()}" for m in missing)
        )
    return parsed


# Sections whose text (or, for topics, the chosen topic) goes to the provider.
# "never" is left out of the unedited check: the example's rules are real rules,
# so keeping them as they are is a legitimate profile.
CHECKED_SECTIONS = ("topics", "beat", "voice", "experience", "hashtags")


def _bullet_text(line: str) -> str:
    return re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()


def _placeholder_lines(example: dict[str, str]) -> set[str]:
    """The example's own placeholder lines, whole and stripped: its bullets that
    start with '(' and its '#Tag' lines. Taken from the shipped file, so they
    can't drift from it."""
    lines = set()
    for name in CHECKED_SECTIONS:
        for line in example.get(name, "").splitlines():
            if _bullet_text(line).startswith(("(", "#")):
                lines.add(line.strip())
    return lines


def unfilled_sections(profile: dict[str, str], example: dict[str, str]) -> list[str]:
    """Names of the sections still holding the example profile's text: the body
    equals the example's, or it keeps one of the example's placeholder lines
    exactly. A real line that merely starts with '(' is not a placeholder."""
    placeholders = _placeholder_lines(example)
    unfilled = []
    for name in CHECKED_SECTIONS:
        body = profile.get(name, "")
        if not body:
            continue
        lines = {line.strip() for line in body.splitlines()}
        if body == example.get(name) or lines & placeholders:
            unfilled.append(name)
    return unfilled


def topic_menu(profile: dict[str, str]) -> list[str]:
    """Topics from the profile's '## Topics' section, else the built-in
    catalog. One topic per line; '-' and '*' bullets and numbering are
    stripped."""
    raw = profile.get("topics", "")
    topics = []
    for line in raw.splitlines():
        line = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
        if line and not line.startswith("#"):
            topics.append(line)
    return topics or list(TOPIC_CATALOG)


def match_topic(topics: list[str], requested: str) -> str:
    """--topic as a menu number, a case-insensitive substring of a menu
    entry, or free text that is not in the menu at all."""
    if requested.isdigit() and 1 <= int(requested) <= len(topics):
        return topics[int(requested) - 1]
    matches = [t for t in topics if requested.lower() in t.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise SystemExit("Ambiguous --topic. Matches:\n  " + "\n  ".join(matches))
    return requested  # free-text topic, not in the menu
