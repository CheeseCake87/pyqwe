import argparse


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


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(ArgumentParser, self).__init__(*args, **kwargs)
        self.program = {key: kwargs[key] for key in kwargs}
        self.options = []

    def print_help(self, file=None):
        print("\n\rUsage: pyqwe <command>")
        print("\n\rCommands:")
        print(" -h, --help => Show the help message and exit")
        print(" -v, --version => Show the version and exit")
        print("\n\rCommands in pyproject.toml:")
        if not self.options:
            print(f" {Colr.WARNING}No commands found in pyproject.toml{Colr.END}")
        else:
            for option in self.options:
                print(
                    f" {Colr.OKBLUE}{option[0]}{Colr.END} "
                    f"{Colr.BOLD}=>{Colr.END} "
                    f"{Colr.OKCYAN}{option[1]}{Colr.END}"
                )
        print("")
