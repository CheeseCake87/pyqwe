import subprocess
import sys
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest

RunPyqwe = Callable[..., "subprocess.CompletedProcess[str]"]


@pytest.fixture
def project(tmp_path: Path) -> Callable[[str], Path]:
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

    pyqwe reads its config at import time, so it has to run in its own process.
    """

    def _run(
        cwd: Path, *args: str, stdin: str = ""
    ) -> "subprocess.CompletedProcess[str]":
        return subprocess.run(
            [sys.executable, "-c", "import pyqwe; pyqwe.main()", *args],
            cwd=cwd,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=30,
        )

    return _run
