import sys
import traceback
from pathlib import Path

from .exceptions import InvalidRunner
from .helpers import _run, _split_runner, Colr
from .parser import ArgumentParser

try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib
    except ImportError:
        raise ImportError("pyqwe requires toml, install it with 'pip install toml'")

__version__ = "1.7.1"

_cwd = Path().cwd()
_known_toml_files = [
    _cwd / "pyqwe.toml",
    _cwd / "pyproject.toml",
]


def _find_toml_file() -> Path:
    for file in _known_toml_files:
        if file.exists():
            return file
    raise FileNotFoundError("pyproject.toml or pyqwe.toml file not found")


_toml_file = _find_toml_file()
_pyproject = tomllib.loads(_toml_file.read_text())

if _toml_file.name == "pyqwe.toml":
    if _pyproject.get("tool", {}).get("pyqwe", {}):
        _qwe = _pyproject.get("tool", {}).get("pyqwe", {})
    else:
        _qwe = _pyproject
else:
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
            print(f" {Colr.WARNING}No commands found, looking in: {_toml_file.name}{Colr.END}")
        else:
            for option in pars.options:

                try:
                    if not isinstance(option[1], str):
                        raise InvalidRunner()
                except Exception as e:
                    _ = e
                    print(f"💥🏎️⁉️ {Colr.FAIL}Invalid runner: {option}{Colr.END}")
                    print("")
                    sys.exit(0)

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
        traceback.print_exc()
        print(f"💥🏎️⁉️ {Colr.FAIL}{e}{Colr.END}")
