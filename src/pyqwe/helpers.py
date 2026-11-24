"""
Parsing and validation of runner strings.
"""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exceptions import InvalidRunner, NotAModuleOrPackage


class Colr:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"

    @classmethod
    def disable(cls) -> None:
        for name in vars(cls).copy():
            if name.isupper():
                setattr(cls, name, "")


GROUP_MODES = ("@step", "@sync", "@async")

# *[shell][(folder)][>]
_TERMINAL_PREFIX = re.compile(
    r"^\*(?P<shell>shell)?(?:\((?P<cwd>[^()]*)\))?(?P<accepts_args>>)?$"
)

# package.module[.py]
_PYTHON_TARGET = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*(\.py)?$")

# ~10~ at the start of a runner part
_SLEEP = re.compile(r"^\s*~(\d+)~\s*")

# {{ VAR_NAME }}
_ENV_VAR = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


@dataclass(frozen=True)
class TerminalPrefix:
    shell: bool
    cwd: str | None
    accepts_args: bool


def split_runner(runner: str) -> tuple[str, str]:
    """
    Split a runner into its start and end, on the first ':'.
    """
    sr, _, er = runner.partition(":")
    return sr, er


def is_terminal_runner(sr: str) -> bool:
    return sr.strip().startswith("*")


def parse_terminal_prefix(sr: str) -> TerminalPrefix:
    """
    Parse the start of a terminal runner, e.g. '*', '*shell', '*(folder)>'.
    """
    match = _TERMINAL_PREFIX.match(sr.strip())
    if not match:
        raise InvalidRunner(
            f"Invalid terminal runner prefix {sr!r}, "
            "expected '*', '*shell', '*(folder)' or '*shell(folder)', "
            "optionally followed by '>'"
        )
    return TerminalPrefix(
        shell=match["shell"] is not None,
        cwd=match["cwd"],
        accepts_args=match["accepts_args"] is not None,
    )


def accepts_extra_args(sr: str) -> bool:
    if not is_terminal_runner(sr):
        return False
    try:
        return parse_terminal_prefix(sr).accepts_args
    except InvalidRunner:
        return False


def parse_sleep(text: str) -> tuple[int, str]:
    """
    Split a leading '~10~' sleep marker from a runner part.
    """
    match = _SLEEP.match(text)
    if not match:
        return 0, text.strip()
    return int(match[1]), text[match.end() :].strip()


def is_python_target(target: str) -> bool:
    return bool(_PYTHON_TARGET.match(target))


def validate_runner(runner: Any) -> None:
    """
    Raise InvalidRunner if the runner is not something pyqwe can run.
    """
    if isinstance(runner, str):
        if runner.startswith("@"):
            raise InvalidRunner(
                f"{runner!r} is a group mode, it must be the first item of a list"
            )
        if ":" not in runner:
            raise InvalidRunner(
                f"Runner is missing ':', expected '<module>:<function>' "
                f"or '*:<command>': {runner!r}"
            )

        sr, er = split_runner(runner)

        if is_terminal_runner(sr):
            parse_terminal_prefix(sr)
            return

        _, target = parse_sleep(sr)
        if "{{" not in target and not is_python_target(target):
            raise InvalidRunner(
                f"Invalid Python runner {runner!r}, expected '<module>:<function>'"
            )
        if not er.strip():
            raise InvalidRunner(f"Python runner is missing a function: {runner!r}")
        return

    if isinstance(runner, list):
        if not all(isinstance(r, str) for r in runner):
            raise InvalidRunner(f"All runners in a group must be strings: {runner!r}")

        body = runner
        if runner and runner[0].startswith("@"):
            if runner[0] not in GROUP_MODES:
                raise InvalidRunner(
                    f"Unknown group mode {runner[0]!r}, "
                    f"expected one of {', '.join(GROUP_MODES)}"
                )
            body = runner[1:]

        if not body:
            raise InvalidRunner("Group has no runners")
        for r in body:
            validate_runner(r)
        return

    raise InvalidRunner(
        f"Runner must be a string or a list of strings, got {type(runner).__name__}"
    )


def resolve_python_module(target: str, root: Path) -> str:
    """
    Turn 'package.module' or 'module.py' into an importable module name,
    checking that it exists relative to the project folder.
    """
    module_name = target.strip().removesuffix(".py")
    path = root.joinpath(*module_name.split("."))

    is_package = path.is_dir() and (path / "__init__.py").exists()
    is_module = path.with_name(f"{path.name}.py").exists()

    if not (is_package or is_module):
        raise NotAModuleOrPackage(f"{path} is not a Python module or package")

    return module_name


def find_env_vars(text: str) -> list[str]:
    """
    Return the names of the {{ VAR }} markers in text.
    """
    return _ENV_VAR.findall(text)


def substitute_env_vars(
    text: str, environ: Mapping[str, str] = os.environ
) -> tuple[str, list[str]]:
    """
    Replace {{ VAR }} markers with their values, returning the new text and the
    names of any variables that are not set.
    """
    missing: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        name = match[1]
        if name in environ:
            return environ[name]
        missing.append(name)
        return match[0]

    return _ENV_VAR.sub(_replace, text), missing
