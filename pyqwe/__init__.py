import tomllib
from pathlib import Path

from .helpers import *
from .parser import ArgumentParser

__version__ = "0.5.0"

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

    for entry, runner in _qwe.items():
        pars.options.append((entry, runner))
        _ = subp.add_parser(entry)
        _.set_defaults(entry=entry, runner=runner)

    args = pars.parse_args()

    try:
        _run(*_split_runner(args.runner), _cwd=_cwd)
    except AttributeError as e:
        _ = e
        pars.print_help()
