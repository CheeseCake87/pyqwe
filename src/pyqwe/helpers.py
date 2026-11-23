import importlib
import importlib.util
import os
import re
import shlex
import subprocess
import sys
import tomllib
import typing as t
from pathlib import Path
from time import sleep

from pyqwe import printer

from .exceptions import (
    FunctionNotFound,
    InvalidRunner,
    NotAFunction,
    NotAModuleOrPackage,
)


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


def load_toml(file: Path) -> dict[str, t.Any]:
    return tomllib.loads(file.read_text())


def find_toml_file(cwd: Path) -> Path:
    _known_toml_files = [
        cwd / "pyqwe.toml",
        cwd / "pyproject.toml",
    ]

    for file in _known_toml_files:
        if file.exists() and file.is_file():
            return file

    raise FileNotFoundError("No pyqwe.toml or pyproject.toml file found")


def get_toml(cwd: Path) -> tuple[Path, dict[str, t.Any]]:
    """
    Specifically set defaults to {} to avoid errors when the toml file is empty.
    """
    toml_file = find_toml_file(cwd)
    raw_toml = load_toml(toml_file)

    # Attempt to find [tool.pyqwe] in the toml file
    tool_pyqwe = raw_toml.get("tool", {}).get("pyqwe", {})

    if toml_file.name == "pyqwe.toml":
        if tool_pyqwe:
            return toml_file, tool_pyqwe
        return toml_file, raw_toml
    return toml_file, tool_pyqwe


def no_traceback_eh(*_: t.Any, **__: t.Any) -> None:
    pass


def split_runner(runner_: str) -> tuple[str, str]:
    r = runner_.split(":")
    sr = r[0]  # start or runner

    if len(r) > 2:
        er = ":".join(r[1:])  # end of runner
    else:
        er = r[1]  # end of runner

    return sr, er


def validate_runner(runner: t.Any) -> None:
    """
    Raise InvalidRunner if the runner is not something pyqwe can run.
    """
    if isinstance(runner, str):
        if runner.startswith("@"):
            raise InvalidRunner(f"Runner cannot start with '@': {runner!r}")
        if ":" not in runner:
            raise InvalidRunner(
                f"Runner is missing ':', expected '<module>:<function>' "
                f"or '*:<command>': {runner!r}"
            )
        return

    if isinstance(runner, list):
        if not all(isinstance(r, str) for r in runner):
            raise InvalidRunner(f"All runners in a group must be strings: {runner!r}")
        body = runner[1:] if runner and runner[0].startswith("@") else runner
        if not body:
            raise InvalidRunner("Group has no runners")
        for r in body:
            validate_runner(r)
        return

    raise InvalidRunner(
        f"Runner must be a string or a list of strings, got {type(runner).__name__}"
    )


def identify_start_of_runner_type(sr_: str, _cwd: Path) -> tuple[Path, str]:
    if sr_.endswith(".py"):
        sr_.replace(".py", "")

    if "." in sr_:
        if sys.platform == "win32":
            sr = _cwd / sr_.replace(".", "\\")

        else:
            sr = _cwd / sr_.replace(".", "/")

    else:
        sr = _cwd / sr_

    if sr.is_dir() and (sr / "__init__.py").exists():
        # sr is a package
        return sr, "package"

    if Path(f"{sr}.py").exists():
        # sr is a module
        return Path(f"{sr}.py"), "module"

    raise NotAModuleOrPackage(f"{sr} is not a Python module or package\n")


def convert_path_to_module(path: Path) -> str:
    file_ = path.stem
    path_ = path.parent
    return f"{path_.name}.{file_}"


def try_dotenv_import(cwd: Path, env_files: list[str]) -> bool:
    try:
        from dotenv import load_dotenv  # type: ignore

        if env_files:
            for env_file in env_files:
                this_file = cwd / env_file
                if not this_file.exists():
                    printer.error_()
                    raise FileNotFoundError(f"Environment file {env_file} not found")

                load_dotenv(env_file)
        else:
            load_dotenv()

        return True

    except ImportError:
        return False


def find_env_vars(
    r: str, env_marker_start: str = "{{", env_marker_end: str = "}}"
) -> list[str]:
    if env_marker_start and env_marker_end in r:
        return [
            i.split(env_marker_end)[0]
            for i in r.split(env_marker_start)
            if env_marker_end in i
        ]

    return []


def extract_and_replace_env_vars(
    sr: str, er: str, _settings: dict[str, str | t.Any]
) -> tuple[str, str, list[str]]:
    extra_dotenv = _settings.get("extra_dotenv", False)
    env_ignore = _settings.get("env_ignore", False)
    env_marker_start = "{{"
    env_marker_end = "}}"

    if env_ignore:
        return sr, er, []

    sr_env_vars = find_env_vars(sr, env_marker_start, env_marker_end)
    er_env_vars = find_env_vars(er, env_marker_start, env_marker_end)
    all_env_vars_not_found = []

    if sr_env_vars or er_env_vars:
        if not extra_dotenv:
            if _settings["env_ignore"] is False:
                printer.error_()
                printer.env_vars_no_dotenv()
                sys.exit()

        else:
            for env_var in sr_env_vars:
                runner_part, envs_not_found = replace_env_vars(
                    env_var, sr, env_marker_start, env_marker_end
                )

                sr = runner_part
                all_env_vars_not_found.extend(envs_not_found)

            for env_var in er_env_vars:
                runner_part, envs_not_found = replace_env_vars(
                    env_var, er, env_marker_start, env_marker_end
                )

                er = runner_part
                all_env_vars_not_found.extend(envs_not_found)

    return sr, er, all_env_vars_not_found


def replace_env_vars(
    env_var: str, runner_part: str, env_marker_start: str, env_marker_end: str
) -> tuple[str, list[str]]:
    not_found = []
    env_var_stripped = env_var.replace(" ", "")

    if not os.getenv(env_var_stripped):
        not_found.append(env_var_stripped)
    else:
        runner_part = runner_part.replace(
            f"{env_marker_start}{env_var}{env_marker_end}",
            os.getenv(env_var_stripped, ""),
        )

    return runner_part, not_found


def list_process_and_pre_check_env_vars(
    runner: list[str], _settings: dict[str, str | t.Any]
) -> list[tuple[str, str, str, list[str]]]:
    sr_er = []

    if runner and runner[0].startswith("@"):
        runner = runner[1:]

    for r in runner:
        sr, er = split_runner(r)

        # check if there are environment variables in the runner
        sr, er, envs_vars_not_found = extract_and_replace_env_vars(sr, er, _settings)

        sr_er.append((r, sr, er, envs_vars_not_found))

    return sr_er


def str_process_and_pre_check_env_vars(
    runner: str, _settings: dict[str, str | t.Any]
) -> tuple[str, str, str, list[str]]:
    if runner[0] == "@":
        printer.error_()
        raise ValueError("Runner cannot start with '@'")

    sr, er = split_runner(runner)

    # check if there are environment variables in the runner
    env_sr, env_er, envs_vars_not_found = extract_and_replace_env_vars(
        sr, er, _settings
    )

    return runner, env_sr, env_er, envs_vars_not_found


def accepts_extra_args(sr: str) -> bool:
    return sr.startswith("*") and ">" in re.sub(r"\(.*?\)", "", sr)


def run_clear() -> None:
    # Clear screen, clear scrollback, move cursor to top left
    print("\033[2J\033[3J\033[H", end="", flush=True)


def check_for_sleep(runner: str) -> str:
    strip_runner = runner.strip()

    if strip_runner.startswith("~"):
        found = re.findall(r"~\d+~", strip_runner)

        if found:
            raw_value = found[0]
            clean_runner = strip_runner.replace(raw_value, "")

            try:
                sleep_for = int(raw_value.replace("~", ""))
                printer.starting_runner_after_sleep(clean_runner, sleep_for)
                sleep(sleep_for)
            except ValueError:
                raise ValueError(f"Invalid sleep time: {runner}, must be an number")

            return clean_runner.strip()

    return strip_runner


def run(sr: str, er: str, _cwd: Path, _settings: dict[str, str | t.Any]) -> int:
    """
    Run a single runner and return its exit code.

    sr: start of runner
    er: end of runner
    """

    try:
        if "*" in sr:
            end_location_runner = check_for_sleep(er)

            printer.starting_runner()

            if "(" in sr:
                _cwd_tack = sr[sr.find("(") + 1 : sr.find(")")]

                if sys.platform == "win32":
                    _cwd_tack = _cwd_tack.replace("/", "\\")

                _cwd = _cwd / _cwd_tack

            extra_args: list[str] = []
            if accepts_extra_args(sr):
                extra_args = list(_settings.get("extra_args", []))

            if "shell" in sr or sys.platform == "win32":
                if extra_args:
                    if sys.platform == "win32":
                        joined_args = subprocess.list2cmdline(extra_args)
                    else:
                        joined_args = shlex.join(extra_args)
                    end_location_runner = f"{end_location_runner} {joined_args}"

                return subprocess.run(
                    end_location_runner, shell=True, cwd=_cwd
                ).returncode

            return subprocess.run(
                shlex.split(end_location_runner) + extra_args, cwd=_cwd
            ).returncode

        else:
            start_location_runner = check_for_sleep(sr)

            printer.starting_runner()

            sr_path, sr_type = identify_start_of_runner_type(
                start_location_runner, _cwd
            )

            if sr_type == "package":
                sys.path.append(str(sr_path.parent))
                module = importlib.import_module(sr_path.name)
            else:
                sys.path.append(str(_cwd))
                module = importlib.import_module(start_location_runner)

            if not hasattr(module, er):
                raise FunctionNotFound(f"\n{er} function not found \n({sr})\n")

            try:
                getattr(module, er)()
            except TypeError:
                raise NotAFunction(f"\n{er} is not a function. \n({sr})\n")

            return 0

    except KeyboardInterrupt:
        if sys.excepthook is sys.__excepthook__:
            sys.excepthook = no_traceback_eh
        raise
