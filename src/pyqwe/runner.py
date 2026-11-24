import os
import shlex
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import printer
from .exceptions import EnvVarNotFound, InvalidRunner, UsageError
from .helpers import (
    GROUP_MODES,
    is_python_target,
    is_terminal_runner,
    parse_sleep,
    parse_terminal_prefix,
    resolve_python_module,
    split_runner,
    substitute_env_vars,
    validate_runner,
)

# Windows always runs terminal runners through the shell, so that commands
# like `npm` (npm.cmd) and shell built-ins like `echo` can be found.
ALWAYS_SHELL = sys.platform == "win32"


@dataclass(frozen=True)
class Step:
    """
    A single runner, with environment variables substituted, ready to run.
    """

    raw: str
    root: Path
    cwd: Path
    sleep: int = 0
    # Terminal runners
    command: str | None = None
    shell: bool = False
    extra_args: tuple[str, ...] = ()
    # Python runners
    module: str | None = None
    function: str | None = None

    @property
    def is_python(self) -> bool:
        return self.module is not None

    def terminal_command(self) -> str | list[str]:
        """
        The command as a string to run in a shell, or as a list of arguments.
        """
        assert self.command is not None

        if self.shell or ALWAYS_SHELL:
            if not self.extra_args:
                return self.command
            if sys.platform == "win32":
                joined = subprocess.list2cmdline(self.extra_args)
            else:
                joined = shlex.join(self.extra_args)
            return f"{self.command} {joined}"

        return shlex.split(self.command) + list(self.extra_args)

    def python_command(self) -> list[str]:
        assert self.module is not None and self.function is not None
        # -P stops the working directory shadowing pyqwe's own modules,
        # pyqwe._call puts the project folder first on sys.path instead.
        return [
            sys.executable,
            "-P",
            "-m",
            "pyqwe._call",
            str(self.root),
            self.module,
            self.function,
        ]

    def describe(self) -> str:
        """
        A human readable description of what this step will run.
        """
        if self.is_python:
            return f"python {self.module}:{self.function}"

        command = self.terminal_command()
        text = command if isinstance(command, str) else shlex.join(command)

        if self.cwd != self.root:
            text = f"(in {os.path.relpath(self.cwd, self.root)}) {text}"
        if self.shell or ALWAYS_SHELL:
            text = f"(shell) {text}"
        return text


def _build_step(
    raw: str, sr: str, er: str, root: Path, extra_args: Sequence[str]
) -> Step:
    if is_terminal_runner(sr):
        prefix = parse_terminal_prefix(sr)
        sleep, command = parse_sleep(er)

        if not command:
            raise InvalidRunner(f"Terminal runner has no command: {raw!r}")

        cwd = root / prefix.cwd if prefix.cwd else root
        if not cwd.is_dir():
            raise InvalidRunner(f"Folder not found: {prefix.cwd!r} in {raw!r}")

        return Step(
            raw=raw,
            root=root,
            cwd=cwd,
            sleep=sleep,
            command=command,
            shell=prefix.shell,
            extra_args=tuple(extra_args) if prefix.accepts_args else (),
        )

    sleep, target = parse_sleep(sr)
    function = er.strip()

    if not is_python_target(target):
        raise InvalidRunner(
            f"Invalid Python runner {raw!r}, expected '<module>:<function>'"
        )
    if not function.isidentifier():
        raise InvalidRunner(f"Invalid function name {function!r} in {raw!r}")

    return Step(
        raw=raw,
        root=root,
        cwd=root,
        sleep=sleep,
        module=resolve_python_module(target, root),
        function=function,
    )


def resolve_runner(
    runner: str | list[str],
    root: Path,
    extra_args: Sequence[str] = (),
    env_ignore: bool = False,
    env_hint: str = "",
) -> tuple[str | None, list[Step]]:
    """
    Validate a runner and resolve it into steps, returning the group mode
    (None for a single runner) and the steps.

    Nothing runs if any part of the runner is invalid or any environment
    variable is missing.
    """
    validate_runner(runner)

    mode: str | None = None
    raws: list[str]

    if isinstance(runner, str):
        raws = [runner]
    elif runner[0] in GROUP_MODES:
        mode, raws = runner[0], runner[1:]
    else:
        mode, raws = "@async", runner

    parts: list[tuple[str, str, str]] = []
    missing: list[str] = []

    for raw in raws:
        sr, er = split_runner(raw)
        if not env_ignore:
            sr, sr_missing = substitute_env_vars(sr)
            er, er_missing = substitute_env_vars(er)
            missing.extend(sr_missing + er_missing)
        parts.append((raw, sr, er))

    if missing:
        names = ", ".join(dict.fromkeys(missing))
        raise EnvVarNotFound(f"Environment variables not found: {names}{env_hint}")

    steps = [_build_step(raw, sr, er, root, extra_args) for raw, sr, er in parts]

    if extra_args and not any(step.extra_args for step in steps):
        raise UsageError(
            "Extra arguments were given, but this command does not accept them. "
            "Use '*>:...' to allow extra arguments."
        )

    return mode, steps


def run_step(step: Step) -> int:
    """
    Run a step and return its exit code.
    """
    if step.sleep:
        printer.waiting(step.describe(), step.sleep)
        time.sleep(step.sleep)

    printer.starting_runner(step.describe())

    if step.is_python:
        return subprocess.run(step.python_command(), cwd=step.root).returncode

    command = step.terminal_command()

    if isinstance(command, str):
        return subprocess.run(command, shell=True, cwd=step.cwd).returncode

    try:
        return subprocess.run(command, cwd=step.cwd).returncode
    except FileNotFoundError:
        printer.error(f"Command not found: {command[0]}")
        return 127
