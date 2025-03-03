"""
This module contains the all the print statements used.
"""

import traceback
from pathlib import Path

from .helpers import Colr


def br():
    """
    Print a spacer line.
    """
    print("")


def no_commands_found(toml_file: Path):
    """
    Print a message when no commands are found.
    """
    print(f" {Colr.WARNING}No commands found, looking in: {toml_file.name}{Colr.END}")


def invalid_runner(option: str):
    """
    Print a message when an invalid runner is found.
    """
    print(f"💥🏎️⁉️{Colr.FAIL}Invalid runner: {option}{Colr.END}")
    br()


def env_vars_no_dotenv():
    print(
        f"{Colr.FAIL}Environment variables set but python-dotenv is not installed.{Colr.END}"
        "\n\r\n\r"
        "pip install python-dotenv"
        "\n\r\n\r"
        "You can ignore this message by setting:"
        "\n\r"
        "[tool.pyqwe]"
        "\n\r"
        "`__IGNORE_DOTENV__ = true`"
        "\n\r"
    )


def invalid_choice():
    print(f" {Colr.FAIL}Invalid choice{Colr.END}")


def soft_crash(error):
    print(f"💥🏎️⁉️{Colr.FAIL}{error}{Colr.END}")


def crash(error: Exception):
    traceback.print_exc()
    print(f"💥🏎️⁉️{Colr.FAIL}{error}{Colr.END}")


def error_():
    print(f"{Colr.FAIL}{Colr.BOLD}ERROR{Colr.END}{Colr.END}")


def message_(message: str):
    print(f"{Colr.FAIL}{Colr.BOLD}{message}{Colr.END}{Colr.END}")


def menu_start():
    print(
        f"🚥|🏎️ {Colr.FAIL}{Colr.BOLD}0 :{Colr.END}{Colr.END} {Colr.FAIL}Exit{Colr.END}"
    )


def menu_option(index: int, runner: str):
    print(
        f"{Colr.BOLD}{Colr.OKCYAN}{index : 3}{Colr.END}{Colr.END} : {Colr.HEADER}{runner}{Colr.END}"
    )


def option_value_list(name: str, value: list):
    print(f"{Colr.HEADER}{name}{Colr.END} {Colr.BOLD}↩︎{Colr.END}  ")
    for func in value:
        print(f"  {Colr.BOLD}=>{Colr.END} {Colr.OKBLUE}{func}{Colr.END}")


def option_value(name, value):
    print(
        f"{Colr.HEADER}{name}{Colr.END} "
        f"{Colr.BOLD}=>{Colr.END} "
        f"{Colr.OKBLUE}{value}{Colr.END}"
    )


def about_to_start_runner(func: str):
    br()
    print(f"🚥|🏎️ {Colr.OKGREEN}About to start runner:{Colr.END}")
    print(f"{Colr.OKBLUE}{func}{Colr.END}")


def starting_runner_after_sleep(func: str, sleep_time: int):
    br()
    print(f"⏱️|🏎️ {Colr.OKGREEN}Waiting {sleep_time} seconds to start runner:{Colr.END}")
    print(f"{Colr.OKBLUE}{func}{Colr.END}")


def runner_skipped():
    print(f"🚧🏎 {Colr.FAIL}Runner skipped{Colr.END}")


def starting_runner():
    print(f"🏎💨 {Colr.OKGREEN}Starting runner{Colr.END}")


def starting_step_runners():
    print(
        f"🟢🏎💨🛑🏎 {Colr.OKGREEN}Starting runners in STEP{Colr.END} {Colr.FAIL}(ctrl + c to abort){Colr.END}"
    )


def starting_sync_runners():
    print(f"🏎💨⏱️ {Colr.OKGREEN}Starting runners in SYNC{Colr.END}")


def starting_async_runners():
    print(f"🏎💨🏎💨🏎💨 {Colr.OKGREEN}Starting runners in ASYNC{Colr.END}")


def runner_done():
    print(f"🏁🏎 {Colr.OKGREEN}Runner done{Colr.END}")


def runner_stopped():
    print(f" 🏁🏎 {Colr.OKGREEN}Runner stopped{Colr.END}")


def runners_stopped():
    print(f"🏁🏎🏎🏎 {Colr.OKGREEN}Runners stopped{Colr.END}")


def runners_aborted():
    print(f"🚧🏎🏎🏎 {Colr.FAIL}Runners aborted{Colr.END}")


def help_():
    print(
        "\n\r"
        f"{Colr.OKGREEN}pyqwe{Colr.END}"
        "\n\r\n\r"
        " Running pyqwe without any option or command will "
        "show all available commands in a menu you can choose from."
        "\n\r\n\r"
        f"{Colr.OKGREEN}pyqwe{Colr.END} {Colr.OKCYAN}<option / command>{Colr.END}"
        "\n\r\n\r"
        f" {Colr.OKCYAN}list, ls{Colr.END} => List all commands found in pyproject.toml"
        "\n\r"
        f" {Colr.OKCYAN}<command>{Colr.END} => Will run the command specified in pyproject.toml"
        "\n\r"
        f" {Colr.OKCYAN}-h, --help{Colr.END} => Show the help message and exit"
        "\n\r"
        f" {Colr.OKCYAN}-v, --version{Colr.END} => Show the version and exit"
        "\n\r\n\r"
        f"{Colr.WARNING}pyproject.toml command format:{Colr.END}"
        "\n\r\n\r"
        "[tool.pyqwe]"
        "\n\r"
        "<command> = <runner>"
        "<command> = [<list>, <of>, <runners>]"
        "\n\r\n\r"
        f"{Colr.WARNING}pyqwe.toml command format:{Colr.END}"
        "\n\r\n\r"
        "<command> = <runner>"
        "<command> = [<list>, <of>, <runners>]"
        "\n\r\n\r"
        f"{Colr.WARNING}Runner guide:{Colr.END}"
        "\n\r\n\r"
        f"{Colr.BOLD}Python Module / Package Runner:{Colr.END}"
        "\n\r\n\r"
        " 'package or module:function to run'"
        "\n\r\n\r"
        f" {Colr.BOLD}Examples:{Colr.END}"
        "\n\r"
        " run_this = 'my_py_file:run_this' > will run run_this function in my_py_file.py"
        "\n\r"
        " run_this = 'my_package:run_this' > will run the run_this function in the __init__.py of my_package"
        "\n\r"
        " run_this = 'my_package.inside:run_this' > will run run_this function in my_package/inside.py"
        "\n\r\n\r"
        f"{Colr.BOLD}Terminal Runner:{Colr.END}"
        "\n\r\n\r"
        " '* or *shell or *(folder) or *shell(folder):command'"
        "\n\r\n\r"
        f" {Colr.BOLD}Examples:{Colr.END}"
        "\n\r"
        " run_this = '*:echo hello' > Run in terminal"
        "\n\r"
        " run_this = '*shell:echo hello' > Run in terminal using shell"
        "\n\r"
        " run_this = '*shell(folder):echo hello' > Run in terminal using shell from the specified relative folder"
        "\n\r\n\r"
        f"{Colr.BOLD}Grouped Runner:{Colr.END}"
        "\n\r\n\r"
        " Run a group of commands in step sequence, sequence or parallel, running in parallel ignores blocking."
        "\n\r\n\r"
        " Parallel (@async) is the default."
        "\n\r\n\r"
        f" {Colr.BOLD}Run in Step:{Colr.END}"
        "\n\r"
        """ \
run_this = [
 '@step',
 '*:echo hello 1'
 '*:echo hello 2'
 '*:echo hello 3'
]
        """
        "\n\r"
        f" {Colr.BOLD}Run in Sync:{Colr.END}"
        "\n\r"
        """ \
run_this = [
 '@sync',
 '*:echo hello 1'
 '*:echo hello 2'
 '*:echo hello 3'
]
        """
        "\n\r"
        f" {Colr.BOLD}Run in Async:{Colr.END}"
        "\n\r"
        """ \
run_this = [
 '@async',  # can be omitted
 '*:echo hello 1'
 '*:echo hello 2'
 '*:echo hello 3'
]
        """
        "\n\r"
        f"For a more detailed guide, visit {Colr.OKCYAN}https://github.com/CheeseCake87/pyqwe/blob/main/README.md{Colr.END}"
    )
