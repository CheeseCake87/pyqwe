import argparse
import importlib
import importlib.util
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

__version__ = "0.1.0"


class NotAPythonPackageError(Exception):
    pass


def _no_traceback_eh(exc_type, exc_val, traceback):
    pass


_cwd = Path().cwd()
_pyproject_file = _cwd / "pyproject.toml"

if not _pyproject_file.exists():
    raise FileNotFoundError("pyproject.toml not found")

_pyproject = tomllib.loads(_pyproject_file.read_text())
_qwe = _pyproject.get("tool", {}).get("qwe")

if not _qwe or not isinstance(_qwe, dict):
    raise ValueError("tool.qwe not found in pyproject.toml")


def _split_runner(runner_: str) -> tuple:
    r = runner_.split(":")
    sr = r[0]  # start or runner
    er = r[1].lower()  # end of runner
    return sr, er


def _path_to_module(path: Path) -> str:
    file = path.stem
    path = path.parent
    return f"{path.name}.{file}"


def _run(sr: str, er: str):
    try:

        if "*" in sr:
            if "cmd" in sr:
                if "shell" in sr:
                    subprocess.run(er, shell=True)
                else:
                    subprocess.run(shlex.split(er))

        else:
            package = _cwd / sr
            init_module = package / "__init__.py"

            if not init_module.exists():
                module = _cwd / f"{sr}.py"

                if not module.exists():
                    raise FileNotFoundError(f"File {module} not found")

                sys.path.append(str(_cwd))
                module = importlib.import_module(sr)
                getattr(module, er)()

            else:
                sys.path.append(str(package))
                module = importlib.import_module("__init__")
                getattr(module, er)()

    except KeyboardInterrupt:
        if sys.excepthook is sys.__excepthook__:
            sys.excepthook = _no_traceback_eh
        raise


def main():
    parser = argparse.ArgumentParser(
        prog="qwe",
        description="Run commands set in the pyproject.toml file",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"qwe {__version__}"
    )

    subparser = parser.add_subparsers()

    for entry, runner in _qwe.items():
        _ = subparser.add_parser(entry, help=runner)
        _.set_defaults(entry=entry, runner=runner)

    args = parser.parse_args()
    _run(*_split_runner(args.runner))


if __name__ == "__main__":
    main()
