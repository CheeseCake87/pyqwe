import argparse

from pyqwe.helpers import Colr


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(ArgumentParser, self).__init__(*args, **kwargs)
        self.program = {key: kwargs[key] for key in kwargs}
        self.options = []

    def print_help(self, file=None):
        print("\n\r"
              "Usage: pyqwe <option> "
              "\n\r\n\r"
              f" {Colr.OKCYAN}list{Colr.END} => List all commands found in pyproject.toml"
              "\n\r"
              f" {Colr.OKCYAN}-h, --help{Colr.END} => Show the help message and exit"
              "\n\r"
              f" {Colr.OKCYAN}-v, --version{Colr.END} => Show the version and exit"
              )
        print("")
