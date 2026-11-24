from pathlib import Path
from typing import Any

import pytest

from pyqwe.exceptions import InvalidRunner, NotAModuleOrPackage
from pyqwe.helpers import (
    TerminalPrefix,
    accepts_extra_args,
    find_env_vars,
    parse_sleep,
    parse_terminal_prefix,
    resolve_python_module,
    split_runner,
    substitute_env_vars,
    validate_runner,
)


@pytest.mark.parametrize(
    ("runner", "expected"),
    [
        ("app:run", ("app", "run")),
        ("*:echo hi", ("*", "echo hi")),
        ("*shell(web)>:npm run", ("*shell(web)>", "npm run")),
        ("*:echo http://example.com", ("*", "echo http://example.com")),
    ],
)
def test_split_runner(runner: str, expected: tuple[str, str]) -> None:
    assert split_runner(runner) == expected


@pytest.mark.parametrize(
    "runner",
    [
        "app:run",
        "*:echo hi",
        ["*:echo 1", "*:echo 2"],
        ["@sync", "*:echo 1"],
        ["@step", "app:run", "*:echo 2"],
        ["@async", "*:echo 1"],
        "app.py:run",
        "pkg.sub:run",
        "~10~ app:run",
        "*shell(web)>:npm run",
        "*:~10~ echo hi",
        "{{ MODULE }}:run",
    ],
)
def test_validate_runner_accepts_valid(runner: Any) -> None:
    validate_runner(runner)


@pytest.mark.parametrize(
    ("runner", "message"),
    [
        ([], "Group has no runners"),
        (["@sync"], "Group has no runners"),
        ("echo hi", "missing ':'"),
        (["*:echo 1", "echo 2"], "missing ':'"),
        ("@sync", "must be the first item"),
        (["@synch", "*:echo 1"], "Unknown group mode '@synch'"),
        (["*:echo 1", "@sync"], "must be the first item"),
        ("*sh:echo hi", "Invalid terminal runner prefix"),
        ("*shell>(web):echo hi", "Invalid terminal runner prefix"),
        ("my app:run", "Invalid Python runner"),
        ("app/run:main", "Invalid Python runner"),
        ("app:", "missing a function"),
        (["*:echo 1", 2], "must be strings"),
        (42, "got int"),
        ({"a": "*:echo"}, "got dict"),
    ],
)
def test_validate_runner_rejects_invalid(runner: Any, message: str) -> None:
    with pytest.raises(InvalidRunner, match=message):
        validate_runner(runner)


@pytest.mark.parametrize(
    ("sr", "expected"),
    [
        ("*", False),
        ("*shell", False),
        ("*>", True),
        ("*shell>", True),
        ("*(web)>", True),
        ("*shell(web)>", True),
        ("*(a>b)", False),
        ("app", False),
    ],
)
def test_accepts_extra_args(sr: str, expected: bool) -> None:
    assert accepts_extra_args(sr) is expected


def test_find_env_vars() -> None:
    assert find_env_vars("echo {{ A }} {{B}} {{ not a var }}") == ["A", "B"]
    assert find_env_vars("echo nothing") == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("echo hi", (0, "echo hi")),
        ("  echo hi ", (0, "echo hi")),
        ("~10~ echo hi", (10, "echo hi")),
        ("~0~echo hi", (0, "echo hi")),
        ("echo ~10~", (0, "echo ~10~")),
    ],
)
def test_parse_sleep(text: str, expected: tuple[int, str]) -> None:
    assert parse_sleep(text) == expected


@pytest.mark.parametrize(
    ("sr", "expected"),
    [
        ("*", TerminalPrefix(shell=False, cwd=None, accepts_args=False)),
        ("*shell", TerminalPrefix(shell=True, cwd=None, accepts_args=False)),
        ("*(web)", TerminalPrefix(shell=False, cwd="web", accepts_args=False)),
        ("*shell(web)>", TerminalPrefix(shell=True, cwd="web", accepts_args=True)),
        (" *> ", TerminalPrefix(shell=False, cwd=None, accepts_args=True)),
        # A folder name containing "shell" must not turn on shell mode
        (
            "*(shell_scripts)",
            TerminalPrefix(shell=False, cwd="shell_scripts", accepts_args=False),
        ),
    ],
)
def test_parse_terminal_prefix(sr: str, expected: TerminalPrefix) -> None:
    assert parse_terminal_prefix(sr) == expected


@pytest.mark.parametrize("sr", ["*sh", "*shellx", "*(web", "*>(web)", "**"])
def test_parse_terminal_prefix_rejects_invalid(sr: str) -> None:
    with pytest.raises(InvalidRunner):
        parse_terminal_prefix(sr)


def test_resolve_python_module(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("")
    (tmp_path / "pkg" / "sub").mkdir(parents=True)
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "sub" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "mod.py").write_text("")

    assert resolve_python_module("app", tmp_path) == "app"
    assert resolve_python_module("app.py", tmp_path) == "app"
    assert resolve_python_module("pkg", tmp_path) == "pkg"
    assert resolve_python_module("pkg.sub", tmp_path) == "pkg.sub"
    assert resolve_python_module("pkg.mod", tmp_path) == "pkg.mod"

    with pytest.raises(NotAModuleOrPackage):
        resolve_python_module("missing", tmp_path)


def test_substitute_env_vars() -> None:
    environ = {"A": "1", "EMPTY": ""}

    assert substitute_env_vars("x{{ A }}y{{EMPTY}}z", environ) == ("x1yz", [])
    assert substitute_env_vars("{{ A }} {{ B }} {{B}}", environ) == (
        "1 {{ B }} {{B}}",
        ["B", "B"],
    )
