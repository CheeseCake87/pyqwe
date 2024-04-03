import sys
import tomllib
from pathlib import Path

from .helpers import _run, _split_runner, Colr
from .parser import ArgumentParser

__version__ = "1.3.0"

# sr = start of runner
# er = end of runner
# runner = sr:er
# flask = app:run
# will invoke the run function in the app module

_cwd = Path().cwd()
_pyproject_file = _cwd / "pyproject.toml"

if not _pyproject_file.exists():
    raise FileNotFoundError("pyproject.toml not found")

_pyproject = tomllib.loads(_pyproject_file.read_text())
_qwe = _pyproject.get("tool", {}).get("pyqwe", {})


def main():
    pars = ArgumentParser(prog="pyqwe", add_help=False)
    pars.add_argument("--version", "-v", action="version", version=f"qwe {__version__}")
    pars.add_argument("--help", "-h", action="help")
    subp = pars.add_subparsers()

    list_parser = subp.add_parser("list")
    list_parser.set_defaults(list=False)

    ls_parser = subp.add_parser("ls")
    ls_parser.set_defaults(list=False)

    for entry, runner in _qwe.items():
        pars.options.append((entry, runner))
        _ = subp.add_parser(entry)
        _.set_defaults(entry=entry, runner=runner)

    args = pars.parse_args()

    if hasattr(args, "list") or hasattr(args, "ls"):
        print("")
        if not pars.options:
            print(f" {Colr.WARNING}No commands found in pyproject.toml{Colr.END}")
        else:
            for option in pars.options:
                print(
                    f" {Colr.OKCYAN}{option[0]}{Colr.END} "
                    f"{Colr.BOLD}=>{Colr.END} "
                    f"{Colr.HEADER}{option[1]}{Colr.END}"
                )
        print("")
        sys.exit(0)

    try:
        _run(*_split_runner(args.runner), _cwd=_cwd)
    except AttributeError as e:
        _ = e
        pars.print_help()
