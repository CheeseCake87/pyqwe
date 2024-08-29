import sys
from pathlib import Path

from .helpers import _run, _split_runner, Colr
from .parser import ArgumentParser

try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib
    except ImportError:
        raise ImportError("pyqwe requires toml, install it with 'pip install toml'")

__version__ = "1.6.0"

_cwd = Path().cwd()
_pyproject_file = _cwd / "pyproject.toml"

if not _pyproject_file.exists():
    raise FileNotFoundError("pyproject.toml not found")

_pyproject = tomllib.loads(_pyproject_file.read_text())
_qwe = _pyproject.get("tool", {}).get("pyqwe", {})


def main():
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

    if hasattr(args, "runner"):
        _runner = args.runner

    else:
        if pars.errored:
            sys.exit(0)

        choice, choice_index = pars.print_chooser(_qwe)

        if not choice or not choice.isdigit():
            sys.exit(0)

        if int(choice) == 0:
            sys.exit(0)

        if int(choice) > len(pars.options):
            print(f" {Colr.FAIL}Invalid choice{Colr.END}")
            sys.exit(0)

        _runner = _qwe.get(choice_index[int(choice) - 1])

    try:
        _run(*_split_runner(_runner), _cwd=_cwd)
    except Exception as e:
        if "pyqwe: error: argument" in str(e):
            print(f" {Colr.FAIL}Invalid argument [{_runner}]{Colr.END}")
        else:
            print(f" {Colr.FAIL}{e}{Colr.END}")
