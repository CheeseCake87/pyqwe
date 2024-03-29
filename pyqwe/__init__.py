import argparse
import importlib
import importlib.util
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path

__version__ = "0.2.0"

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
_qwe = _pyproject.get("tool", {}).get("pyqwe")

if not _qwe or not isinstance(_qwe, dict):
    raise ValueError("tool.qwe not found in pyproject.toml")


class NotAModuleOrPackage(Exception):
    pass


class FunctionNotFound(Exception):
    pass


class NotAFunction(Exception):
    pass


def _no_traceback_eh(exc_type, exc_val, traceback):
    pass


def _split_runner(runner_: str) -> tuple:
    r = runner_.split(":")
    sr = r[0]  # start or runner
    er = r[1].lower()  # end of runner
    return sr, er


def _identify_sr(sr_: str) -> tuple[Path, str]:
    if sr_.endswith(".py"):
        sr_.replace(".py", "")

    if "." in sr_:
        if sys.platform == "win32":
            sr = _cwd / sr_.replace(".", "\\")

        else:
            sr = _cwd / sr_.replace(".", "/")

    else:
        sr = _cwd / sr_

    if sr.is_dir() and (sr / "__init__.py").exists():
        # sr is a package
        return sr, "package"

    if Path(f"{sr}.py").exists():
        # sr is a module
        return Path(f"{sr}.py"), "module"

    raise NotAModuleOrPackage(f"\n{sr} is not a Python module or package\n")


def _path_to_module(path: Path) -> str:
    file_ = path.stem
    path_ = path.parent
    return f"{path_.name}.{file_}"


def _run(sr: str, er: str):
    try:
        if "*" in sr:
            if "shell" in sr:
                subprocess.run(er, shell=True)
            else:
                subprocess.run(shlex.split(er))

        else:
            sr_path, sr_type = _identify_sr(sr)

            if sr_type == "package":
                sys.path.append(str(sr_path))
                module = importlib.import_module("__init__")
            else:
                sys.path.append(str(_cwd))
                module = importlib.import_module(sr)

            if not hasattr(module, er):
                raise FunctionNotFound(f"\n{er} function not found \n({sr})\n")

            try:
                getattr(module, er)()
            except TypeError:
                raise NotAFunction(f"\n{er} is not a function. \n({sr})\n")

    except KeyboardInterrupt:
        if sys.excepthook is sys.__excepthook__:
            sys.excepthook = _no_traceback_eh
        raise


def main():
    parser = argparse.ArgumentParser(
        prog="qwe",
        description="Run commands set in the pyproject.toml file",
    )

    parser.add_argument("--version", action="version", version=f"qwe {__version__}")

    subparser = parser.add_subparsers()

    for entry, runner in _qwe.items():
        _ = subparser.add_parser(entry, help=runner)
        _.set_defaults(entry=entry, runner=runner)

    args = parser.parse_args()
    _run(*_split_runner(args.runner))


if __name__ == "__main__":
    main()
