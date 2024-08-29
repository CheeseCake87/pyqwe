import argparse

from pyqwe.helpers import Colr


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(ArgumentParser, self).__init__(*args, **kwargs)
        self.program = {key: kwargs[key] for key in kwargs}
        self.options = []
        self.errored = False

    def print_help(self, file=None):
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
        )
        print("")

    def print_usage(self, file=None):
        pass

    def error(self, message):
        if "list" in message and "invalid choice:" in message:
            print(f"{Colr.FAIL}{Colr.BOLD}ERROR{Colr.END}{Colr.END}")
            self.errored = True
        else:
            print(f"{Colr.FAIL}{Colr.BOLD}{message}{Colr.END}{Colr.END}")
            self.errored = True

    @staticmethod
    def print_chooser(runners: dict):
        print("")
        print(f"{Colr.OKGREEN}{Colr.BOLD}Available commands:{Colr.END}{Colr.END}")
        print(f"{Colr.FAIL}{Colr.BOLD}0.{Colr.END}{Colr.END} {Colr.FAIL}Exit{Colr.END}")
        runner_index = []
        for index, runner in enumerate(runners):
            runner_index.append(runner)
            print(f"{Colr.BOLD}{index + 1}.{Colr.END} {Colr.OKCYAN}{runner}{Colr.END}")

        return input(f"{Colr.WARNING}Select a command to run [0]: {Colr.END}"), runner_index
