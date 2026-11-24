import os
import subprocess
import sys
import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass
class Result:
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


RunPyqwe = Callable[..., Result]
Project = Callable[[str], Path]

# Pretend python-dotenv is not installed: a None entry in sys.modules makes
# `import dotenv` raise ImportError
_NO_DOTENV = "import sys; sys.modules['dotenv'] = None; "


@pytest.fixture
def project(tmp_path: Path) -> Project:
    """
    Write a pyqwe.toml into a temporary project folder and return the folder.
    """

    def _make(toml: str) -> Path:
        (tmp_path / "pyqwe.toml").write_text(textwrap.dedent(toml))
        return tmp_path

    return _make


@pytest.fixture
def run_pyqwe() -> RunPyqwe:
    """
    Run pyqwe as a real process in the given folder.

    -P stops Python adding the working directory to sys.path, matching how the
    installed `pyqwe` script runs.
    """

    def _run(
        cwd: Path,
        *args: str,
        stdin: str = "",
        env: dict[str, str] | None = None,
        dotenv: bool = True,
    ) -> Result:
        code = ("" if dotenv else _NO_DOTENV) + "import pyqwe; pyqwe.main()"

        run_env = {
            k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "FORCE_COLOR")
        }
        run_env.update(env or {})

        result = subprocess.run(
            [sys.executable, "-P", "-c", code, *args],
            cwd=cwd,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=30,
            env=run_env,
        )
        return Result(result.returncode, result.stdout, result.stderr)

    return _run
