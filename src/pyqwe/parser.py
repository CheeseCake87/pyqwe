import argparse
from typing import Any

from pyqwe import printer
from pyqwe.helpers import Colr


class ArgumentParser(argparse.ArgumentParser):
    program: dict[str, Any]
    options: list[Any]
    errored: bool

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(ArgumentParser, self).__init__(*args, **kwargs)
        self.program = {key: kwargs[key] for key in kwargs}
        self.options = []
        self.errored = False

    def print_help(self, *args: Any, **kwargs: Any) -> None:
        printer.help_()
        printer.br()

    def print_usage(self, *args: Any, **kwargs: Any) -> None:
        pass

    def error(self, message: str) -> Any:
        if "list" in message and "invalid choice:" in message:
            printer.error_()
            self.errored = True
        else:
            printer.message_(message)
            self.errored = True

    @staticmethod
    def print_chooser(runners: dict[str, Any]) -> tuple[str, list[Any]]:
        runner_index = []
        for index, runner in enumerate(runners):
            runner_index.append(runner)
            printer.menu_option(index + 1, runner)

        return input(
            f"{Colr.WARNING}Select a command to run [0]: {Colr.END}"
        ), runner_index
