import importlib
import importlib.util
import os
import shlex
import subprocess
import sys
from pathlib import Path

from .exceptions import (
    FunctionNotFound,
    NotAModuleOrPackage,
    NotAFunction,
    EnvVarNotFound,
)


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


def _extra_rev() -> callable:
    try:
        from pyqwe_extra_dotenv import _replace_env_vars  # noqa
    except ImportError:
        raise ImportError("pyqwe_extra_dotenv package was not found")

    return _replace_env_vars


def _no_traceback_eh(exc_type, exc_val, traceback):
    pass


def _split_runner(runner_: str) -> tuple:
    r = runner_.split(":")
    sr = r[0]  # start or runner
    er = r[1]  # end of runner
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

    raise NotAModuleOrPackage(f"{sr} is not a Python module or package\n")


def _path_to_module(path: Path) -> str:
    file_ = path.stem
    path_ = path.parent
    return f"{path_.name}.{file_}"


def _extract_env_vars(r: str) -> list[str]:
    if "{{" and "}}" in r:
        return [i.split("}}")[0].replace(" ", "") for i in r.split("{{") if "}}" in i]
    return []


def _import_python_dotenv() -> bool:
    try:
        import dotenv

        dotenv.load_dotenv()

        return True

    except ImportError:
        return False


def _replace_env_vars(r: str) -> str:
    env_vars_ = _extract_env_vars(r)
    python_dotenv_import_attempted = False

    for env_var in env_vars_:
        if not os.getenv(env_var):
            # if env_var is not found
            raise EnvVarNotFound(
                "\n\r\n\r"
                f"{Colr.FAIL}Environment variable {env_var} was not found.{Colr.END}"
                "\n\r"
            )

        r = r.replace(f"{{{{{env_var}}}}}", os.getenv(env_var))

    return r


def _run(sr: str, er: str, _cwd: Path):
    extra_dotenv = importlib.util.find_spec("pyqwe_extra_dotenv")
    if extra_dotenv:
        rev = _extra_rev()
    else:
        rev = _replace_env_vars

    sr = rev(sr)
    er = rev(er)

    try:
        if "*" in sr:
            if "(" in sr:
                _cwd_tack = sr[sr.find("(") + 1: sr.find(")")]

                if sys.platform == "win32":
                    _cwd_tack = _cwd_tack.replace("/", "\\")

                _cwd = _cwd / _cwd_tack

            if "shell" in sr:
                subprocess.run(er, shell=True, cwd=_cwd)
            else:
                subprocess.run(shlex.split(er), cwd=_cwd)

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
