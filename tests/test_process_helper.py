"""REPO-08: the tests start a process only through tests/_proc.py, which holds one noqa.

tests/acceptance/ is frozen and has its own helpers, so it is left out.
"""

import ast
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
PROC = TESTS / "_proc.py"

# module -> attributes that start a process; "*" means any attribute with the given prefix.
STARTERS = {
    "subprocess": {"run", "Popen", "call", "check_call", "check_output", "getoutput"}
    | {"getstatusoutput"},
    "os": {"system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp"},
    "pty": {"spawn", "fork"},
    "multiprocessing": {"Process"},
}
STARTER_PREFIXES = {"os": ("spawn", "exec"), "asyncio": ("create_subprocess_",)}


def starts_a_process(call: ast.Call) -> str | None:
    func = call.func
    if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)):
        return None
    module, attribute = func.value.id, func.attr
    if attribute in STARTERS.get(module, set()):
        return f"{module}.{attribute}"
    if attribute.startswith(STARTER_PREFIXES.get(module, ())):
        return f"{module}.{attribute}"
    return None


def other_test_files() -> list[Path]:
    return [path for path in sorted(TESTS.glob("*.py")) if path != PROC]


def test_the_helper_and_the_test_files_are_found() -> None:
    assert PROC.exists()
    assert other_test_files()


@pytest.mark.parametrize("path", other_test_files(), ids=lambda path: path.name)
def test_no_other_test_starts_a_process(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = [
        f"line {node.lineno}: {name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and (name := starts_a_process(node))
    ]
    assert not found, f"{path.name} starts a process outside tests/_proc.py: {found}"


def test_the_helper_holds_exactly_one_noqa_for_s603() -> None:
    noqa = [line for line in PROC.read_text(encoding="utf-8").splitlines() if "noqa" in line]
    assert len(noqa) == 1
    assert "noqa: S603" in noqa[0]
    assert noqa[0].split("# noqa: S603", 1)[1].strip(" #")  # the reason follows the code


def test_the_guard_recognises_a_starter() -> None:
    call = ast.parse("subprocess.run(['x'])").body[0].value  # type: ignore[attr-defined]
    assert starts_a_process(call) == "subprocess.run"
    tame = ast.parse("subprocess.CompletedProcess(['x'], 0)").body[0].value  # type: ignore[attr-defined]
    assert starts_a_process(tame) is None
