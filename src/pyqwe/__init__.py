import importlib.metadata
import sys
import threading
from functools import partial
from pathlib import Path
from typing import Any, NoReturn

from pyqwe import printer

from .exceptions import EnvVarNotFound, InvalidRunner
from .helpers import (
    Colr,
    accepts_extra_args,
    get_toml,
    list_process_and_pre_check_env_vars,
    run,
    run_clear,
    split_runner,
    str_process_and_pre_check_env_vars,
    try_dotenv_import,
    validate_runner,
)
from .parser import ArgumentParser

__version__ = importlib.metadata.version(__package__ or __name__)

CWD = Path().cwd()
TOML_FILE, QWE = get_toml(CWD)


def _run_one(sr: str, er: str, settings: dict[str, Any]) -> int:
    """
    Run a single runner and return its exit code, never raising.

    A Ctrl+C returns 130, an unexpected error returns 1.
    """
    try:
        exit_code = run(sr, er, _cwd=CWD, _settings=settings)

    except KeyboardInterrupt:
        printer.runner_stopped()
        return 130

    except Exception as e:
        printer.crash(e)
        return 1

    if exit_code != 0:
        printer.runner_failed(exit_code)

    return exit_code


def _exit_invalid_runner(name: str, error: InvalidRunner) -> NoReturn:
    printer.invalid_runner(f"{name} => {error}")
    sys.exit(1)


def main() -> NoReturn:
    pars = ArgumentParser(prog="pyqwe", add_help=False)
    pars.add_argument(
        "--version", "-v", action="version", version=f"pyqwe {__version__}"
    )
    pars.add_argument("--help", "-h", action="help")
    subp = pars.add_subparsers()

    list_parser = subp.add_parser("list")
    list_parser.set_defaults(list=False)

    ls_parser = subp.add_parser("ls")
    ls_parser.set_defaults(list=False)

    clear_terminal = QWE.get("__clear_terminal__", False)
    env_ignore = QWE.get("__env_ignore__", False)
    env_marker_start = "{{"
    env_marker_end = "}}"
    env_files = QWE.get("__env_files__", [])
    if not isinstance(env_ignore, bool):
        raise ValueError("__env_ignore__ must be a boolean")
    if not isinstance(clear_terminal, bool):
        raise ValueError("__clear_terminal__ must be a boolean")
    if not isinstance(env_files, list):
        raise ValueError("__env_files__ must be a list")

    # Commands are everything that is not a __setting__ and not a sub-table
    # (sub-tables, e.g. [tool.pyqwe.group.*], are not supported as commands)
    commands: dict[str, Any] = {
        key: value
        for key, value in QWE.items()
        if not (key.startswith("__") and key.endswith("__"))
        and not isinstance(value, dict)
    }

    settings: dict[str, Any] = {
        "clear_terminal": clear_terminal,
        "env_ignore": env_ignore,
        "env_marker_start": env_marker_start,
        "env_marker_end": env_marker_end,
        "extra_dotenv": try_dotenv_import(CWD, env_files),
    }

    if settings["clear_terminal"]:
        run_clear()

    for entry, entry_runner in commands.items():
        pars.options.append((entry, entry_runner))
        _ = subp.add_parser(entry)
        _.set_defaults(entry=entry, runner=entry_runner)

    # Anything after a command name is treated as extra arguments for the
    # runner, these are only passed on to runners marked with '>' (*>:...)
    argv = sys.argv[1:]
    extra_args: list[str] = []
    if argv and argv[0] in commands:
        extra_args = argv[1:]
        argv = argv[:1]

    settings["extra_args"] = extra_args

    args = pars.parse_args(argv)

    ####################
    # COMMAND: list, ls
    if hasattr(args, "list") or hasattr(args, "ls"):
        printer.br()

        if not pars.options:
            printer.no_commands_found(TOML_FILE)
        else:
            for name, value in pars.options:
                if not isinstance(value, (str, list)):
                    printer.invalid_runner(f"{name} => {value!r}")
                    sys.exit(1)

                if isinstance(value, list):
                    printer.option_value_list(name, value)
                else:
                    printer.option_value(name, value)

        printer.br()
        sys.exit(0)

    ####################
    # COMMAND: <runnner>
    if hasattr(args, "runner"):
        name = args.entry
        runner = args.runner

    ####################
    # COMMAND: None
    else:
        if pars.errored:
            # Unknown command or bad arguments
            sys.exit(2)

        try:
            choice, choice_index = pars.print_chooser(commands)
        except (KeyboardInterrupt, EOFError):
            printer.br()
            sys.exit(130)

        if not choice or not choice.isdigit() or int(choice) == 0:
            sys.exit(0)

        if int(choice) > len(pars.options):
            printer.invalid_choice()
            sys.exit(1)

        name = choice_index[int(choice) - 1]
        runner = commands[name]

    try:
        validate_runner(runner)
    except InvalidRunner as e:
        _exit_invalid_runner(name, e)

    if extra_args:
        runner_parts = runner if isinstance(runner, list) else [runner]
        if not any(
            ":" in r and accepts_extra_args(split_runner(r)[0]) for r in runner_parts
        ):
            printer.error_()
            printer.message_(
                "Extra arguments were given, but this command does not accept them. "
                "Use '*>:...' to allow extra arguments."
            )
            sys.exit(2)

    ####################
    # If runner is a single command
    if isinstance(runner, str):
        runner, sr, er, env_vars_not_found = str_process_and_pre_check_env_vars(
            runner, settings
        )

        if env_vars_not_found:
            printer.error_()
            raise EnvVarNotFound(
                f"Environment variables not found: {', '.join(env_vars_not_found)}"
            )

        sys.exit(_run_one(sr, er, settings))

    ####################
    # If runner is a group
    mode = runner[0] if runner[0].startswith("@") else "@async"

    extracted_runners = list_process_and_pre_check_env_vars(runner, settings)

    # Fail if any environment variables are not found in the list of runners
    all_env_vars_not_found = []
    for extracted in extracted_runners:
        _, _, _, env_vars_not_found = extracted
        all_env_vars_not_found.extend(env_vars_not_found)

    if all_env_vars_not_found:
        printer.error_()
        raise EnvVarNotFound(
            f"Environment variables not found: {', '.join(all_env_vars_not_found)}"
        )

    # The group exits with the first non-zero exit code
    group_exit_code = 0

    if mode == "@step":  # RUNNERS IN STEP
        printer.starting_step_runners()

        for extracted_runner, sr, er, _ in extracted_runners:
            printer.about_to_start_runner(extracted_runner)

            try:
                continue_ = input(f"{Colr.WARNING}Continue? [Y/n]: {Colr.END}")
            except (KeyboardInterrupt, EOFError):
                printer.br()
                printer.runners_aborted()
                sys.exit(group_exit_code or 130)

            if continue_.lower() == "n":
                printer.runner_skipped()
                continue

            exit_code = _run_one(sr, er, settings)
            group_exit_code = group_exit_code or exit_code

            printer.runner_done()

        sys.exit(group_exit_code)

    if mode == "@sync":  # RUNNERS IN SYNC
        printer.starting_sync_runners()

        for _, sr, er, _ in extracted_runners:
            exit_code = _run_one(sr, er, settings)
            group_exit_code = group_exit_code or exit_code

            # Ctrl+C moves on to the next runner, a failure stops the group
            if exit_code not in (0, 130):
                printer.runners_aborted()
                break

        printer.runners_stopped()
        sys.exit(group_exit_code)

    # RUNNERS IN ASYNC (default)
    printer.starting_async_runners()

    exit_codes: list[int] = [0] * len(extracted_runners)

    def _thread_target(index: int, sr: str, er: str) -> None:
        exit_codes[index] = _run_one(sr, er, settings)

    threads = [
        threading.Thread(target=partial(_thread_target, index, sr, er))
        for index, (_, sr, er, _) in enumerate(extracted_runners)
    ]

    try:
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    except KeyboardInterrupt:
        printer.runners_stopped()
        sys.exit(130)

    sys.exit(next((code for code in exit_codes if code != 0), 0))
