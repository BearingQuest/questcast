"""Files: the author profile, and the history, drafts and run log in the data
directory."""

import json
import os
import sys
from datetime import date, datetime

# The rule applies only below Python 3.7 and requires-python is >=3.14.
# nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
from importlib import resources
from pathlib import Path

from questcast import config
from questcast.author_profile import parse_profile

RUN_VIA = ""  # "provider/model, search source" once main() has chosen them (R13)
RUN_TOKENS = ""  # " — tokens: …" once the provider has given counts (R53, R59)


def token_note(usage: dict[str, int] | None, estimate: int) -> str:
    """The provider's token counts and the R53 estimate of the prompt as
    sent, for the OK or FAILED line; empty without counts (R59)."""
    if not usage:
        return ""
    counts = ", ".join(f"{k} {v}" for k, v in usage.items())
    return f" — tokens: {counts}, estimate {estimate}"


def ensure_data_dir() -> Path:
    """Create the data directory if it is missing, with mode 700 since it holds
    the profile, drafts and history. An existing one keeps its mode.

    If it can't be created, stop with a plain message naming the path, the OS's
    reason and the setting that moves it, instead of a traceback.
    """
    data = config.data_dir()
    if data.is_dir():
        return data
    try:
        data.parent.mkdir(parents=True, exist_ok=True)
        data.mkdir(mode=0o700, exist_ok=True)
        data.chmod(0o700)  # mkdir's mode is reduced by the umask
    except OSError as exc:
        raise SystemExit(
            f"Can't create the QuestCast data folder {data}: {exc.strerror or exc}.\n"
            "Set QC_POST_DATA_DIR to a folder you can write to."
        ) from None
    return data


def log_run(message: str) -> None:
    """Append to run.log. Never raises: it runs on the error path, where a
    second failure would hide the first, so a write problem is one stderr line."""
    via = f" [via {RUN_VIA}]" if RUN_VIA else ""
    try:
        ensure_data_dir()
        with config.log_file().open("a") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} {message}{via}\n")
    except (OSError, SystemExit) as exc:
        reason = getattr(exc, "strerror", None) or "data folder can't be created"
        print(f"Could not write the run log {config.log_file()}: {reason}", file=sys.stderr)


def warn(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)
    log_run(f"WARNING — {message}")


def load_profile(path: Path) -> dict:
    """Read and parse the author profile (see author_profile.parse_profile)."""
    if not path.exists():
        raise SystemExit(
            f"No author profile at {path}\n"
            "Run 'qc init' (from a repo clone: 'python daily_post.py init') to create one in "
            "the data directory, or copy questcast/author_profile.example.md to that "
            "path. Then fill it in — it is what makes the posts sound like you."
        )
    return parse_profile(path.read_text(), path)


def example_profile_text() -> str:
    """The example profile shipped inside the package."""
    return resources.files("questcast").joinpath(config.EXAMPLE_PROFILE).read_text()


def example_profile() -> dict[str, str]:
    """The shipped example profile, parsed like a real one."""
    return parse_profile(example_profile_text(), Path(config.EXAMPLE_PROFILE))


def create_profile() -> Path:
    """Copy the example profile to the data directory as author_profile.md,
    with mode 600 (R33). Never overwrites: raises FileExistsError if a file
    (or a symlink) is already there.

    A missing data directory is created with mode 700 (see ensure_data_dir).
    """
    example = example_profile_text().encode()
    ensure_data_dir()
    path = config.profile_file()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(example)
    path.chmod(0o600)  # os.open's mode is reduced by the umask
    return path


def load_history() -> list:
    history_file = config.history_file()
    if history_file.exists():
        try:
            return json.loads(history_file.read_text())
        except json.JSONDecodeError:
            print(f"WARNING: {history_file} is corrupt; starting fresh.", file=sys.stderr)
    return []


def save_history(history: list) -> None:
    config.history_file().write_text(json.dumps(history, indent=2))


def log_drafts(
    item: dict,
    topic: str,
    x_post: str,
    li_post: str,
    x_link: str,
    li_link: str,
    via: str = "",
) -> None:
    ensure_data_dir()
    entry = (
        f"\n---\n\n# {date.today().isoformat()} — {item['title']}\n\n"
        f"Topic: {topic}\n"
        f"Via: {via or 'n/a'}\n"
        f"Source: {item.get('source', 'n/a')}\n"
        f"Why: {item.get('why', 'n/a')}\n\n"
        f"## X\n\n{x_post}\n\n[Post on X]({x_link})\n\n"
        f"## LinkedIn\n\n{li_post}\n\n[Post on LinkedIn]({li_link})\n"
    )
    with config.drafts_file().open("a") as f:
        f.write(entry)
