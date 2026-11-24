"""
End-to-end tests that run pyqwe as a real process against a temporary pyqwe.toml.
"""

import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import Project, RunPyqwe

WINDOWS = sys.platform == "win32"

# The Python running the tests, quoted for the platform's command line
PY = (
    subprocess.list2cmdline([sys.executable])
    if WINDOWS
    else shlex.quote(sys.executable)
)


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
    assert "exit code 3" in result.stderr


def test_missing_executable(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("missing = '*:pyqwe-this-does-not-exist'\n")

    result = run_pyqwe(cwd, "missing")

    if WINDOWS:
        assert result.returncode != 0
    else:
        assert result.returncode == 127
        assert "Command not found: pyqwe-this-does-not-exist" in result.stderr


def test_unknown_command_exits_two(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"ok = {py('print(1)')}\n")

    result = run_pyqwe(cwd, "nope")

    assert result.returncode == 2
    assert "Unknown command 'nope'" in result.stderr


def test_unknown_command_suggests_close_match(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project(f"deploy = {py('print(1)')}\n")

    result = run_pyqwe(cwd, "deplyo")

    assert result.returncode == 2
    assert "did you mean 'deploy'?" in result.stderr


def test_extra_args_to_command_without_marker_exits_two(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project(f"ok = {py('print(1)')}\n")

    result = run_pyqwe(cwd, "ok", "extra")

    assert result.returncode == 2
    assert "does not accept them" in result.stderr


def test_extra_args_are_appended(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"echo_args = '*>:{PY} -c \"import sys; print(sys.argv[1:])\"'\n")

    result = run_pyqwe(cwd, "echo_args", "a", "--flag", "b c")

    assert result.returncode == 0
    assert "['a', '--flag', 'b c']" in result.stdout


# --------------------------------------------------------------------------
# Python runners


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
    assert "RuntimeError: boom" in bad.stderr


def test_python_function_can_set_exit_code(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project("go = 'mod:run'\n")
    (cwd / "mod.py").write_text("import sys\n\ndef run():\n    sys.exit(9)\n")

    assert run_pyqwe(cwd, "go").returncode == 9


def test_python_runner_with_py_suffix(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("go = 'app.py:run'\n")
    (cwd / "app.py").write_text("def run():\n    print('app ran')\n")

    result = run_pyqwe(cwd, "go")

    assert result.returncode == 0
    assert "app ran" in result.stdout


def test_python_runner_in_package_with_relative_import(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project("go = 'pkg.sub:run'\n")
    (cwd / "pkg" / "sub").mkdir(parents=True)
    (cwd / "pkg" / "__init__.py").write_text("")
    (cwd / "pkg" / "helper.py").write_text("MESSAGE = 'relative ok'\n")
    (cwd / "pkg" / "sub" / "__init__.py").write_text(
        "from ..helper import MESSAGE\n\ndef run():\n    print(MESSAGE)\n"
    )

    result = run_pyqwe(cwd, "go")

    assert result.returncode == 0
    assert "relative ok" in result.stdout


def test_local_module_wins_over_installed_package(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    # pytest is installed in the test environment, the local file must win
    cwd = project("go = 'pytest:run'\n")
    (cwd / "pytest.py").write_text("def run():\n    print('local pytest')\n")

    result = run_pyqwe(cwd, "go")

    assert result.returncode == 0
    assert "local pytest" in result.stdout


def test_missing_module_is_an_error(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("go = 'missing:run'\n")

    result = run_pyqwe(cwd, "go")

    assert result.returncode == 1
    assert "is not a Python module or package" in result.stderr
    assert "Traceback" not in result.stderr


def test_missing_function_is_an_error(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("go = 'mod:nope'\n")
    (cwd / "mod.py").write_text("")

    result = run_pyqwe(cwd, "go")

    assert result.returncode == 1
    assert "nope function not found in mod" in result.stderr


def test_type_error_inside_function_is_not_hidden(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project("go = 'mod:run'\n")
    (cwd / "mod.py").write_text("def run():\n    len(1)\n")

    result = run_pyqwe(cwd, "go")

    assert result.returncode == 1
    assert "is not a function" not in result.output
    assert "TypeError" in result.stderr


def test_non_callable_target_is_not_a_function(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project("go = 'mod:VALUE'\n")
    (cwd / "mod.py").write_text("VALUE = 1\n")

    result = run_pyqwe(cwd, "go")

    assert result.returncode == 1
    assert "VALUE is not a function" in result.stderr


def test_async_python_runners_run_in_separate_processes(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project("group = ['a:run', 'b:run']\n")
    (cwd / "a.py").write_text(
        "import os\n\ndef run():\n    print('pid', os.getpid())\n"
    )
    (cwd / "b.py").write_text(
        "import os\n\ndef run():\n    print('pid', os.getpid())\n"
    )

    result = run_pyqwe(cwd, "group")

    pids = {line for line in result.stdout.splitlines() if line.startswith("pid")}
    assert result.returncode == 0
    assert len(pids) == 2


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
    assert "Group has no runners" in result.stderr
    assert "Traceback" not in result.stderr


def test_group_with_only_mode_is_an_error(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project('only_mode = ["@sync"]\n')

    result = run_pyqwe(cwd, "only_mode")

    assert result.returncode == 1
    assert "Group has no runners" in result.stderr


def test_runner_without_colon_is_an_error(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project("bad = 'echo hi'\n")

    result = run_pyqwe(cwd, "bad")

    assert result.returncode == 1
    assert "missing ':'" in result.stderr
    assert "Traceback" not in result.stderr


def test_unknown_group_mode_is_an_error(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"group = ['@synch', {py('print(1001)')}]\n")

    result = run_pyqwe(cwd, "group")

    assert result.returncode == 1
    assert "Unknown group mode" in result.stderr
    assert "1001" not in result.stdout


def test_invalid_runner_in_group_runs_nothing(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project(f"group = ['@sync', {py('print(1001)')}, 'missing:run']\n")

    result = run_pyqwe(cwd, "group")

    assert result.returncode == 1
    assert "1001" not in result.stdout


def test_invalid_terminal_prefix_is_an_error(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project("bad = '*sh:echo hi'\n")

    result = run_pyqwe(cwd, "bad")

    assert result.returncode == 1
    assert "Invalid terminal runner prefix" in result.stderr


def test_missing_folder_is_an_error(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("bad = '*(nope):echo hi'\n")

    result = run_pyqwe(cwd, "bad")

    assert result.returncode == 1
    assert "Folder not found: 'nope'" in result.stderr


@pytest.mark.skipif(WINDOWS, reason="Windows always runs through the shell")
def test_folder_named_shell_does_not_enable_shell(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    # Without a shell, '$HOME' is passed through literally
    cwd = project(
        f"go = '*(shell_scripts):{PY} -c \"import sys; print(sys.argv[1])\" $HOME'\n"
    )
    (cwd / "shell_scripts").mkdir()

    result = run_pyqwe(cwd, "go")

    assert result.returncode == 0
    assert "$HOME" in result.stdout


# --------------------------------------------------------------------------
# Config errors


def test_no_config_file_is_an_error(tmp_path: Path, run_pyqwe: RunPyqwe) -> None:
    result = run_pyqwe(tmp_path, "anything")

    assert result.returncode == 1
    assert "No pyqwe.toml or pyproject.toml file found" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("args", [["-v"], ["--version"], ["-h"], ["--help"]])
def test_version_and_help_work_without_config(
    tmp_path: Path, run_pyqwe: RunPyqwe, args: list[str]
) -> None:
    result = run_pyqwe(tmp_path, *args)

    assert result.returncode == 0
    assert "pyqwe" in result.stdout


def test_invalid_toml_is_an_error(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("this is not toml\n")

    result = run_pyqwe(cwd, "ls")

    assert result.returncode == 1
    assert "Could not read pyqwe.toml" in result.stderr
    assert "Traceback" not in result.stderr


def test_bad_setting_type_is_an_error(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("__clear_terminal__ = 'yes'\nok = '*:echo'\n")

    result = run_pyqwe(cwd, "ok")

    assert result.returncode == 1
    assert "__clear_terminal__ must be true or false" in result.stderr
    assert "Traceback" not in result.stderr


def test_unknown_setting_is_an_error(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("__IGNORE_DOTENV__ = true\nok = '*:echo'\n")

    result = run_pyqwe(cwd, "ok")

    assert result.returncode == 1
    assert "Unknown setting '__IGNORE_DOTENV__'" in result.stderr


def test_invalid_runner_type_is_an_error(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("number = 42\n")

    result = run_pyqwe(cwd, "ls")

    assert result.returncode == 1
    assert "Invalid runner for command 'number'" in result.stderr


# --------------------------------------------------------------------------
# Environment variables


def test_env_var_from_environment_without_dotenv(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project(
        "show = '*:"
        + PY
        + ' -c "import sys; print(sys.argv[1])" {{ PYQWE_TEST_VALUE }}\'\n'
    )

    result = run_pyqwe(cwd, "show", env={"PYQWE_TEST_VALUE": "hello"}, dotenv=False)

    assert result.returncode == 0
    assert "hello" in result.stdout


def test_missing_env_var_is_an_error(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("show = '*:echo {{ PYQWE_TEST_UNSET }}'\n")

    result = run_pyqwe(cwd, "show")

    assert result.returncode == 1
    assert "Environment variables not found: PYQWE_TEST_UNSET" in result.stderr
    assert "Traceback" not in result.stderr


def test_missing_env_var_hints_at_dotenv(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("show = '*:echo {{ PYQWE_TEST_UNSET }}'\n")
    (cwd / ".env").write_text("PYQWE_TEST_UNSET=1\n")

    result = run_pyqwe(cwd, "show", dotenv=False)

    assert result.returncode == 1
    assert "python-dotenv is not installed" in result.stderr


def test_dotenv_file_is_loaded(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(
        "show = '*:"
        + PY
        + ' -c "import sys; print(sys.argv[1])" {{ PYQWE_FROM_DOTENV }}\'\n'
    )
    (cwd / ".env").write_text("PYQWE_FROM_DOTENV=from-dotenv\n")

    result = run_pyqwe(cwd, "show")

    assert result.returncode == 0
    assert "from-dotenv" in result.stdout


def test_env_files_without_dotenv_is_an_error(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project("__env_files__ = ['.env']\nok = '*:echo'\n")
    (cwd / ".env").write_text("")

    result = run_pyqwe(cwd, "ok", dotenv=False)

    assert result.returncode == 1
    assert "python-dotenv is not installed" in result.stderr


def test_missing_env_file_is_an_error(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("__env_files__ = ['.env.missing']\nok = '*:echo'\n")

    result = run_pyqwe(cwd, "ok")

    assert result.returncode == 1
    assert "Environment file not found" in result.stderr


def test_env_ignore_leaves_markers(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(
        "__env_ignore__ = true\n"
        "show = '*:" + PY + ' -c "import sys; print(sys.argv[1])" {{X}}\'\n'
    )

    result = run_pyqwe(cwd, "show")

    assert result.returncode == 0
    assert "{{X}}" in result.stdout


# --------------------------------------------------------------------------
# list / ls


def test_ls_lists_commands_with_help_and_sections(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project(
        """\
        hello = '*:echo hello'
        test = { run = '*:pytest', help = 'Run the tests' }

        [js]
        __header__ = 'JavaScript'
        install = '*(js):npm install'
        """
    )

    result = run_pyqwe(cwd, "ls")

    assert result.returncode == 0
    assert "hello" in result.stdout
    assert "test # Run the tests" in result.stdout
    assert "JavaScript" in result.stdout
    assert "*(js):npm install" in result.stdout


@pytest.mark.parametrize("args", [["ls"], ["list"], ["-l"], ["--list"]])
def test_list_aliases(project: Project, run_pyqwe: RunPyqwe, args: list[str]) -> None:
    cwd = project("hello = '*:echo hello'\n")

    result = run_pyqwe(cwd, *args)

    assert result.returncode == 0
    assert "*:echo hello" in result.stdout


def test_command_named_ls_overrides_builtin(
    project: Project, run_pyqwe: RunPyqwe
) -> None:
    cwd = project(f"ls = {py('print(1006)')}\n")

    result = run_pyqwe(cwd, "ls")
    listing = run_pyqwe(cwd, "--list")

    assert result.returncode == 0
    assert "1006" in result.stdout
    assert listing.returncode == 0
    assert "print(1006)" in listing.stdout


def test_section_commands_can_be_run(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"[tools]\ngo = {py('print(1007)')}\n")

    result = run_pyqwe(cwd, "go")

    assert result.returncode == 0
    assert "1007" in result.stdout


# --------------------------------------------------------------------------
# Dry run


def test_dry_run_shows_but_does_not_run(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(
        """\
        group = ['@sync', '*>:echo {{ PYQWE_DRY }}', '~5~ mod:run', '*:~3~ echo later']
        """
    )
    (cwd / "mod.py").write_text("raise RuntimeError('should not be imported')\n")

    result = run_pyqwe(cwd, "-n", "group", "extra", env={"PYQWE_DRY": "value"})

    assert result.returncode == 0
    assert "group (@sync) would run:" in result.stdout
    assert "echo value extra" in result.stdout
    assert "(after 5s) python mod:run" in result.stdout
    assert "(after 3s)" in result.stdout
    assert "should not be imported" not in result.output


def test_dry_run_still_checks_env_vars(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("show = '*:echo {{ PYQWE_TEST_UNSET }}'\n")

    assert run_pyqwe(cwd, "--dry-run", "show").returncode == 1


# --------------------------------------------------------------------------
# Menu


def test_menu_shows_exit_option(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"ok = {py('print(1)')}\n")

    result = run_pyqwe(cwd, stdin="0\n")

    assert result.returncode == 0
    assert "0...Exit" in result.stdout
    assert "1...ok" in result.stdout


def test_menu_runs_choice(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"fail = {py('import sys; sys.exit(7)')}\n")

    assert run_pyqwe(cwd, stdin="1\n").returncode == 7


def test_menu_invalid_choice_exits_one(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(f"ok = {py('print(1)')}\n")

    result = run_pyqwe(cwd, stdin="99\n")

    assert result.returncode == 1
    assert "Invalid choice" in result.stderr


# --------------------------------------------------------------------------
# Colour


def test_no_colour_when_not_a_terminal(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("hello = '*:echo hello'\n")

    result = run_pyqwe(cwd, "ls")

    assert "\033[" not in result.output


def test_force_colour(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("hello = '*:echo hello'\n")

    result = run_pyqwe(cwd, "ls", env={"FORCE_COLOR": "1"})

    assert "\033[" in result.stdout


def test_no_color_wins_over_force_color(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("hello = '*:echo hello'\n")

    result = run_pyqwe(cwd, "ls", env={"FORCE_COLOR": "1", "NO_COLOR": "1"})

    assert "\033[" not in result.output


# --------------------------------------------------------------------------
# Shell completion


def test_commands_lists_names(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project("one = '*:echo'\n[more]\ntwo = '*:echo'\n")

    result = run_pyqwe(cwd, "--commands")

    assert result.returncode == 0
    assert result.stdout.split() == ["one", "two"]


def test_commands_includes_help(project: Project, run_pyqwe: RunPyqwe) -> None:
    cwd = project(
        """
        one = { run = '*:echo', help = "Say   one,\\n  then stop" }
        two = '*:echo'
        """
    )

    result = run_pyqwe(cwd, "--commands")

    assert result.stdout.splitlines() == ["one\tSay one, then stop", "two"]


def test_commands_is_silent_without_config(tmp_path: Path, run_pyqwe: RunPyqwe) -> None:
    result = run_pyqwe(tmp_path, "--commands")

    assert result.returncode == 0
    assert result.output == ""


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_completion_scripts(tmp_path: Path, run_pyqwe: RunPyqwe, shell: str) -> None:
    result = run_pyqwe(tmp_path, "--completion", shell)

    assert result.returncode == 0
    assert "pyqwe --commands" in result.stdout

    # Check the script parses, if the shell is installed
    shell_path = shutil.which(shell)
    if shell_path and shell != "fish":
        script = tmp_path / f"completion.{shell}"
        script.write_text(result.stdout)
        check = subprocess.run([shell_path, "-n", str(script)], capture_output=True)
        assert check.returncode == 0, check.stderr


@pytest.mark.skipif(WINDOWS or not shutil.which("bash"), reason="needs bash")
@pytest.mark.parametrize(
    ("words", "expected"),
    [
        ("pyqwe ''", ["build", "db:migrate", "test"]),
        ("pyqwe b", ["build"]),
        ("pyqwe -n ''", ["build", "db:migrate", "test"]),
        ("pyqwe --l", ["--list"]),
        ("pyqwe --completion z", ["zsh"]),
        # After the command name, bash falls back to file names
        ("pyqwe test --l", []),
    ],
)
def test_bash_completion(
    project: Project, run_pyqwe: RunPyqwe, words: str, expected: list[str]
) -> None:
    cwd = project(
        """
        build = { run = '*:echo', help = 'Build: everything' }
        "db:migrate" = '*:echo'
        test = '*>:echo'
        """
    )
    script = run_pyqwe(cwd, "--completion", "bash").stdout

    # Stand in for the installed pyqwe script
    pyqwe = f"pyqwe() {{ {PY} -P -c 'import pyqwe; pyqwe.main()' \"$@\"; }}"
    test = (
        f"{pyqwe}\n{script}\n"
        f"COMP_WORDS=({words}); COMP_CWORD=$((${{#COMP_WORDS[@]}} - 1))\n"
        "_pyqwe_complete\n"
        'printf "%s\\n" "${COMPREPLY[@]}"\n'
    )
    result = subprocess.run(
        ["bash", "-c", test], cwd=cwd, capture_output=True, text=True, timeout=30
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == expected
