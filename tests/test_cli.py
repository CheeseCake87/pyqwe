"""
End-to-end tests that run pyqwe as a real process against a temporary pyqwe.toml.
"""

import shlex
import sys
from collections.abc import Callable
from pathlib import Path

from conftest import RunPyqwe

Project = Callable[[str], Path]

# A portable way to print and exit from a terminal runner
PY = shlex.quote(sys.executable)


def py(code: str) -> str:
    """
    A terminal runner that runs a line of Python, as a TOML literal string.
    """
    return f"'*:{PY} -c \"{code}\"'"


# --------------------------------------------------------------------------
# Exit codes


def test_successful_command_exits_zero(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"ok = {py('print(1)')}\n")

    assert run_pyqwe(cwd, "ok").returncode == 0


def test_failing_command_exit_code_is_passed_through(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project(f"fail = {py('import sys; sys.exit(3)')}\n")

    result = run_pyqwe(cwd, "fail")

    assert result.returncode == 3
    assert "exit code 3" in result.stdout


def test_missing_executable_exits_one(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("missing = '*:pyqwe-this-does-not-exist'\n")

    assert run_pyqwe(cwd, "missing").returncode == 1


def test_unknown_command_exits_two(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"ok = {py('print(1)')}\n")

    assert run_pyqwe(cwd, "nope").returncode == 2


def test_extra_args_to_command_without_marker_exits_two(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project(f"ok = {py('print(1)')}\n")

    result = run_pyqwe(cwd, "ok", "extra")

    assert result.returncode == 2
    assert "does not accept them" in result.stdout


def test_python_function_runner(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("good = 'mod:good'\nbad = 'mod:bad'\n")
    (cwd / "mod.py").write_text(
        "def good():\n    print('good ran')\n\n"
        "def bad():\n    raise RuntimeError('boom')\n"
    )

    good = run_pyqwe(cwd, "good")
    bad = run_pyqwe(cwd, "bad")

    assert good.returncode == 0
    assert "good ran" in good.stdout
    assert bad.returncode == 1
    assert "boom" in bad.stdout


# --------------------------------------------------------------------------
# Groups


def test_sync_group_stops_on_first_failure(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project(
        f"""\
        group = [
            "@sync",
            {py("print(1001)")},
            {py("import sys; sys.exit(4)")},
            {py("print(1003)")},
        ]
        """
    )

    result = run_pyqwe(cwd, "group")

    assert result.returncode == 4
    assert "1001" in result.stdout
    assert "1003" not in result.stdout


def test_sync_group_success(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(
        f"""\
        group = ["@sync", {py("print(1001)")}, {py("print(1002)")}]
        """
    )

    result = run_pyqwe(cwd, "group")

    assert result.returncode == 0
    assert "1001" in result.stdout
    assert "1002" in result.stdout


def test_async_group_exits_with_failure(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(
        f"""\
        group = [{py("print(1001)")}, {py("import sys; sys.exit(5)")}]
        """
    )

    assert run_pyqwe(cwd, "group").returncode == 5


def test_step_group_reports_failure(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(
        f"""\
        group = [
            "@step",
            {py("import sys; sys.exit(6)")},
            {py("print(1004)")},
        ]
        """
    )

    result = run_pyqwe(cwd, "group", stdin="y\ny\n")

    # Step mode leaves the decision to the user, so it carries on
    assert result.returncode == 6
    assert "1004" in result.stdout


def test_step_group_skipping_failure_exits_zero(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project(
        f"""\
        group = ["@step", {py("import sys; sys.exit(6)")}, {py("print(1005)")}]
        """
    )

    assert run_pyqwe(cwd, "group", stdin="n\ny\n").returncode == 0


# --------------------------------------------------------------------------
# Invalid runners


def test_empty_group_is_an_error(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("empty = []\n")

    result = run_pyqwe(cwd, "empty")

    assert result.returncode == 1
    assert "Group has no runners" in result.stdout
    assert "Traceback" not in result.stderr


def test_group_with_only_mode_is_an_error(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project('only_mode = ["@sync"]\n')

    result = run_pyqwe(cwd, "only_mode")

    assert result.returncode == 1
    assert "Group has no runners" in result.stdout


def test_runner_without_colon_is_an_error(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project("bad = 'echo hi'\n")

    result = run_pyqwe(cwd, "bad")

    assert result.returncode == 1
    assert "missing ':'" in result.stdout
    assert "Traceback" not in result.stderr


# --------------------------------------------------------------------------
# list / ls


def test_ls_ignores_sub_tables(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(
        """\
        hello = '*:echo hello'

        [group.js]
        install = '*(js):npm install'
        """
    )

    result = run_pyqwe(cwd, "ls")

    assert result.returncode == 0
    assert "hello" in result.stdout
    assert "Invalid runner" not in result.stdout
    assert "npm install" not in result.stdout


def test_sub_table_is_not_a_command(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("[group.js]\ninstall = '*:echo hi'\n")

    assert run_pyqwe(cwd, "group").returncode == 2


def test_ls_with_invalid_runner_type_exits_one(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project("number = 42\n")

    result = run_pyqwe(cwd, "ls")

    assert result.returncode == 1
    assert "Invalid runner" in result.stdout


# --------------------------------------------------------------------------
# Menu


def test_menu_exit_choice(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"ok = {py('print(1)')}\n")

    assert run_pyqwe(cwd, stdin="0\n").returncode == 0


def test_menu_runs_choice(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"fail = {py('import sys; sys.exit(7)')}\n")

    assert run_pyqwe(cwd, stdin="1\n").returncode == 7


def test_menu_invalid_choice_exits_one(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"ok = {py('print(1)')}\n")

    result = run_pyqwe(cwd, stdin="99\n")

    assert result.returncode == 1
    assert "Invalid choice" in result.stdout
