import argparse

from pyqwe import printer
from pyqwe.helpers import Colr


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(ArgumentParser, self).__init__(*args, **kwargs)
        self.program = {key: kwargs[key] for key in kwargs}
        self.options = []
        self.errored = False

    def print_help(self, file=None):
        printer.help_()
        printer.br()

    def print_usage(self, file=None):
        pass

    def error(self, message):
        if "list" in message and "invalid choice:" in message:
            printer.error_()
            self.errored = True
        else:
            printer.message_(message)
            self.errored = True

    @staticmethod
    def print_chooser(runners):
        runner_index = []
        for index, runner in enumerate(runners):
            runner_index.append(runner)
            printer.menu_option(index + 1, runner)

        return input(
            f"{Colr.WARNING}Select a command to run [0]: {Colr.END}"
        ), runner_index
