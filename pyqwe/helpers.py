import importlib
import shlex
import subprocess
import sys
from pathlib import Path

from .exceptions import (
    FunctionNotFound,
    NotAModuleOrPackage,
    NotAFunction,
)


def _no_traceback_eh(exc_type, exc_val, traceback):
    pass


def _split_runner(runner_: str) -> tuple:
    r = runner_.split(":")
    sr = r[0]  # start or runner
    er = r[1].lower()  # end of runner
    return sr, er


def _identify_sr(sr_: str, _cwd: Path) -> tuple[Path, str]:
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


def _run(sr: str, er: str, _cwd: Path):
    try:
        if "*" in sr:
            if "shell" in sr:
                subprocess.run(er, shell=True)
            else:
                subprocess.run(shlex.split(er))

        else:
            sr_path, sr_type = _identify_sr(sr, _cwd)

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


__all__ = [
    "_no_traceback_eh",
    "_split_runner",
    "_identify_sr",
    "_path_to_module",
    "_run",
]
