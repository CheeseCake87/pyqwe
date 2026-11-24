import argparse
import difflib
import importlib.metadata
import sys
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from . import printer
from .completion import SHELLS, completion_script
from .config import Command, Config, load_config, load_env_files
from .exceptions import ConfigError, PyqweError, UsageError
from .runner import Step, resolve_runner, run_step

# Built-in commands, a command in the toml file with the same name wins
BUILTIN_LIST = ("list", "ls")


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        printer.error(message)
        print("Run 'qwe --help' for usage.", file=sys.stderr)
        sys.exit(2)

    def print_help(self, file: object = None) -> None:
        printer.help_()


def _build_parser() -> _Parser:
    version = importlib.metadata.version("pyqwe")

    parser = _Parser(prog="pyqwe", add_help=False)
    parser.add_argument("-h", "--help", action="help")
    parser.add_argument("-v", "--version", action="version", version=f"pyqwe {version}")
    parser.add_argument("-l", "--list", action="store_true")
    parser.add_argument("-n", "--dry-run", action="store_true")
    parser.add_argument("--completion", choices=SHELLS)
    # Used by the completion scripts: print command names, one per line
    parser.add_argument("--commands", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("command", nargs="?")
    # Everything after the command name is passed to '*>:...' runners
    parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> NoReturn:
    sys.exit(run_cli(sys.argv[1:] if argv is None else list(argv)))


def run_cli(argv: list[str]) -> int:
    printer.configure()

    args = _build_parser().parse_args(argv)

    if args.completion:
        print(completion_script(args.completion), end="")
        return 0

    try:
        config = load_config(Path.cwd())
    except ConfigError as e:
        if args.commands:
            return 0
        printer.error(e)
        return e.exit_code

    if args.commands:
        for command in config.commands.values():
            print(_completion_line(command))
        return 0

    try:
        return _dispatch(config, args)
    except PyqweError as e:
        printer.error(e)
        return e.exit_code


def _completion_line(command: Command) -> str:
    """
    A line for the completion scripts: the name, then a tab and the help text
    if there is any. Whitespace in the help text is collapsed so it stays on
    one line.
    """
    if command.help:
        return f"{command.name}\t{' '.join(command.help.split())}"
    return command.name


def _dispatch(config: Config, args: argparse.Namespace) -> int:
    name: str | None = args.command

    if args.list or (name in BUILTIN_LIST and name not in config.commands):
        _print_list(config)
        return 0

    cleared = False

    if name is None:
        if config.clear_terminal and not args.dry_run:
            printer.clear_terminal()
            cleared = True

        choice = _choose(config)
        if isinstance(choice, int):
            return choice
        command = choice

    elif name in config.commands:
        command = config.commands[name]

    else:
        raise UsageError(_unknown_command(name, config))

    dotenv_installed = load_env_files(config)

    env_hint = ""
    if not dotenv_installed and not config.env_ignore:
        if (config.root / ".env").is_file():
            env_hint = (
                " (a .env file was found, but python-dotenv is not installed "
                "to load it, install it with 'pip install python-dotenv')"
            )

    mode, steps = resolve_runner(
        command.runner,
        config.root,
        extra_args=args.args,
        env_ignore=config.env_ignore,
        env_hint=env_hint,
    )

    if args.dry_run:
        printer.dry_run(command.name, mode, [(s.sleep, s.describe()) for s in steps])
        return 0

    if config.clear_terminal and not cleared:
        printer.clear_terminal()

    return _run(mode, steps)


def _unknown_command(name: str, config: Config) -> str:
    message = f"Unknown command {name!r}"
    matches = difflib.get_close_matches(name, list(config.commands), n=1)
    if matches:
        return f"{message}, did you mean {matches[0]!r}?"
    return f"{message}, run 'qwe --list' to see all commands"


def _print_list(config: Config) -> None:
    if not config.commands:
        printer.no_commands_found(config.file)
        return

    printer.br()
    section = None
    for command in config.commands.values():
        if command.section and command.section != section:
            printer.section_header(command.section or "NO VALUE")
            section = command.section
        printer.list_command(command.name, command.runner, command.help)
    printer.br()


def _choose(config: Config) -> Command | int:
    """
    Show the menu, returning the chosen command or an exit code.
    """
    commands = list(config.commands.values())

    if not commands:
        printer.no_commands_found(config.file)
        return 0

    printer.menu_exit()
    section = None
    for index, command in enumerate(commands, start=1):
        if command.section and command.section != section:
            printer.section_header(command.section or "NO VALUE")
            section = command.section
        printer.menu_option(index, command.name, command.help)

    try:
        choice = printer.menu_prompt().strip()
    except (KeyboardInterrupt, EOFError):
        printer.br()
        return 130

    if choice in ("", "0"):
        return 0

    if not choice.isdigit() or not 1 <= int(choice) <= len(commands):
        printer.invalid_choice()
        return 1

    return commands[int(choice) - 1]


# --------------------------------------------------------------------------
# Running


def _run_one(step: Step) -> int:
    """
    Run a single step and return its exit code, never raising.

    A Ctrl+C returns 130, an unexpected error returns 1.
    """
    try:
        exit_code = run_step(step)

    except KeyboardInterrupt:
        printer.runner_stopped()
        return 130

    except Exception as e:
        printer.crash(e)
        return 1

    if exit_code != 0:
        printer.runner_failed(exit_code)

    return exit_code


def _run(mode: str | None, steps: list[Step]) -> int:
    if mode is None:
        return _run_one(steps[0])

    printer.starting_group(mode)

    if mode == "@step":
        return _run_step_group(steps)
    if mode == "@sync":
        return _run_sync_group(steps)
    return _run_async_group(steps)


def _run_step_group(steps: list[Step]) -> int:
    group_exit_code = 0

    for step in steps:
        printer.about_to_start_runner(step.describe())

        try:
            answer = printer.continue_prompt()
        except (KeyboardInterrupt, EOFError):
            printer.br()
            printer.runners_aborted()
            return group_exit_code or 130

        if answer.strip().lower() == "n":
            printer.runner_skipped()
            continue

        group_exit_code = group_exit_code or _run_one(step)
        printer.runner_done()

    return group_exit_code


def _run_sync_group(steps: list[Step]) -> int:
    group_exit_code = 0

    for step in steps:
        exit_code = _run_one(step)
        group_exit_code = group_exit_code or exit_code

        # Ctrl+C moves on to the next runner, a failure stops the group
        if exit_code not in (0, 130):
            printer.runners_aborted()
            return group_exit_code

    printer.runners_stopped()
    return group_exit_code


def _run_async_group(steps: list[Step]) -> int:
    exit_codes = [0] * len(steps)

    def _target(index: int, step: Step) -> None:
        exit_codes[index] = _run_one(step)

    threads = [
        threading.Thread(target=_target, args=(index, step), daemon=True)
        for index, step in enumerate(steps)
    ]

    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        printer.runners_stopped()
        return 130

    return next((code for code in exit_codes if code != 0), 0)
