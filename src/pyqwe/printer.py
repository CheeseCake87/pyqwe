"""
All the output pyqwe prints.

Colour and emoji are turned off by configure() when output is not a
terminal, or when NO_COLOR is set.
"""

import os
import sys
import traceback
from pathlib import Path

from .helpers import Colr

_emoji = True


def configure() -> None:
    """
    Decide whether to use colour and emoji.

    NO_COLOR turns colour off, FORCE_COLOR turns it on, otherwise colour is
    used when stdout is a terminal. Emoji are only used with colour, and only
    when the terminal can print them.
    """
    global _emoji

    if os.environ.get("NO_COLOR"):
        colour = False
    elif os.environ.get("FORCE_COLOR"):
        colour = True
    else:
        colour = sys.stdout.isatty()

    encoding = (sys.stdout.encoding or "").lower().replace("-", "")
    _emoji = colour and encoding.startswith("utf")

    if not colour:
        Colr.disable()


def _e(icon: str) -> str:
    return f"{icon} " if _emoji else ""


def br() -> None:
    print("")


# --------------------------------------------------------------------------
# Errors


def error(message: object) -> None:
    print(
        f"{Colr.FAIL}{Colr.BOLD}Error:{Colr.END} {Colr.FAIL}{message}{Colr.END}",
        file=sys.stderr,
    )


def crash(e: BaseException) -> None:
    traceback.print_exception(e)
    error(e)


# --------------------------------------------------------------------------
# list / ls and the menu


def no_commands_found(toml_file: Path) -> None:
    print(f"{Colr.WARNING}No commands found in {toml_file.name}{Colr.END}")


def section_header(title: str) -> None:
    br()
    print(f"{Colr.BOLD}{Colr.UNDERLINE}{title}{Colr.END}")


def list_command(name: str, runner: str | list[str], help_: str | None) -> None:
    if help_:
        print(f"{Colr.HEADER}{name}{Colr.END} {Colr.OKGREEN}# {help_}{Colr.END}")
    else:
        print(f"{Colr.HEADER}{name}{Colr.END}")

    for line in [runner] if isinstance(runner, str) else runner:
        print(f"  {Colr.BOLD}=>{Colr.END} {Colr.OKBLUE}{line}{Colr.END}")


def menu_exit() -> None:
    print(f"{Colr.BOLD}{Colr.FAIL}{0: 3}{Colr.END}...{Colr.FAIL}Exit{Colr.END}")


def menu_option(index: int, name: str, help_: str | None) -> None:
    text = (
        f"{Colr.BOLD}{Colr.OKCYAN}{index: 3}{Colr.END}...{Colr.HEADER}{name}{Colr.END}"
    )
    if help_:
        text += f" {Colr.OKGREEN}# {help_}{Colr.END}"
    print(text)


def menu_prompt() -> str:
    return input(f"{Colr.WARNING}Select a command to run [0]: {Colr.END}")


def invalid_choice() -> None:
    error("Invalid choice")


# --------------------------------------------------------------------------
# Running


def dry_run(name: str, mode: str | None, steps: list[tuple[int, str]]) -> None:
    title = f"{name} ({mode})" if mode else name
    print(f"{Colr.HEADER}{title}{Colr.END} would run:")
    for sleep, description in steps:
        wait = f"{Colr.WARNING}(after {sleep}s){Colr.END} " if sleep else ""
        print(f"  {Colr.BOLD}=>{Colr.END} {wait}{Colr.OKBLUE}{description}{Colr.END}")


def waiting(description: str, seconds: int) -> None:
    print(
        f"{_e('⏱️')}{Colr.OKGREEN}Waiting {seconds} seconds to start:{Colr.END} "
        f"{Colr.OKBLUE}{description}{Colr.END}"
    )


def starting_runner(description: str) -> None:
    print(
        f"{_e('🏎💨')}{Colr.OKGREEN}Starting:{Colr.END} "
        f"{Colr.OKBLUE}{description}{Colr.END}",
        flush=True,
    )


def about_to_start_runner(description: str) -> None:
    br()
    print(f"{_e('🚥')}{Colr.OKGREEN}About to start:{Colr.END}")
    print(f"{Colr.OKBLUE}{description}{Colr.END}")


def continue_prompt() -> str:
    return input(f"{Colr.WARNING}Continue? [Y/n]: {Colr.END}")


def starting_group(mode: str) -> None:
    labels = {
        "@step": "Starting runners in STEP (ctrl + c to abort)",
        "@sync": "Starting runners in SYNC",
        "@async": "Starting runners in ASYNC",
    }
    print(f"{_e('🏎💨')}{Colr.OKGREEN}{labels[mode]}{Colr.END}")


def runner_failed(exit_code: int) -> None:
    print(
        f"{_e('💥')}{Colr.FAIL}Runner failed with exit code {exit_code}{Colr.END}",
        file=sys.stderr,
    )


def runner_skipped() -> None:
    print(f"{_e('🚧')}{Colr.WARNING}Runner skipped{Colr.END}")


def runner_done() -> None:
    print(f"{_e('🏁')}{Colr.OKGREEN}Runner done{Colr.END}")


def runner_stopped() -> None:
    print(f"{_e('🏁')}{Colr.OKGREEN}Runner stopped{Colr.END}")


def runners_stopped() -> None:
    print(f"{_e('🏁')}{Colr.OKGREEN}Runners stopped{Colr.END}")


def runners_aborted() -> None:
    print(f"{_e('🚧')}{Colr.FAIL}Runners aborted{Colr.END}")


def clear_terminal() -> None:
    # Clear screen, clear scrollback, move cursor to top left
    if sys.stdout.isatty():
        print("\033[2J\033[3J\033[H", end="", flush=True)


# --------------------------------------------------------------------------
# Help


def help_() -> None:
    g, c, w, b, e = Colr.OKGREEN, Colr.OKCYAN, Colr.WARNING, Colr.BOLD, Colr.END
    print(
        f"""
{g}pyqwe{e} - run commands from pyqwe.toml or pyproject.toml

{w}Usage:{e}

  qwe                         Show a menu of commands to choose from
  qwe {c}<command>{e} [args...]     Run a command
  qwe {c}--list{e}                  List all commands (also: qwe list / ls)

{w}Options:{e}

  {c}-l, --list{e}                  List all commands
  {c}-n, --dry-run{e}               Show what a command would run, without running it
  {c}--completion{e} {{bash,zsh,fish}}  Print a shell completion script
  {c}-h, --help{e}                  Show this help message
  {c}-v, --version{e}               Show the version

{w}pyproject.toml example:{e}

  [tool.pyqwe]
  {b}run_module{e} = "my_package.module:function"
  {b}say_hello{e} = "*:echo hello"
  {b}with_help{e} = {{ run = "*:pytest", help = "Run the tests" }}
  {b}group{e} = ["@sync", "*:echo one", "*:echo two"]

{w}(remove [tool.pyqwe] if using pyqwe.toml){e}

{w}Terminal runners:{e}

  '*:command'                 Run a command
  '*shell:command'            Run a command in the shell
  '*(folder):command'         Run a command in a folder
  '*>:command'                Append extra arguments: qwe <command> arg1 arg2
  '*shell(folder)>:command'   All of the above, in this order

{w}Groups:{e}

  '@async' (default)          Run all commands in parallel
  '@sync'                     Run in order, stopping at the first failure
  '@step'                     Run in order, asking before each command

For a more detailed guide, visit {c}https://github.com/CheeseCake87/pyqwe{e}
"""
    )
