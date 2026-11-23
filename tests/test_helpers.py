from typing import Any

import pytest

from pyqwe.exceptions import InvalidRunner
from pyqwe.helpers import (
    accepts_extra_args,
    check_for_sleep,
    find_env_vars,
    list_process_and_pre_check_env_vars,
    split_runner,
    validate_runner,
)

SETTINGS: dict[str, Any] = {"env_ignore": True}


@pytest.mark.parametrize(
    ("runner", "expected"),
    [
        ("app:run", ("app", "run")),
        ("*:echo hi", ("*", "echo hi")),
        ("*shell(web)>:npm run", ("*shell(web)>", "npm run")),
        ("*:echo http://example.com", ("*", "echo http://example.com")),
    ],
)
def test_split_runner(runner: str, expected: tuple[str, str]) -> None:
    assert split_runner(runner) == expected


@pytest.mark.parametrize(
    "runner",
    [
        "app:run",
        "*:echo hi",
        ["*:echo 1", "*:echo 2"],
        ["@sync", "*:echo 1"],
        ["@step", "app:run", "*:echo 2"],
    ],
)
def test_validate_runner_accepts_valid(runner: Any) -> None:
    validate_runner(runner)


@pytest.mark.parametrize(
    ("runner", "message"),
    [
        ([], "Group has no runners"),
        (["@sync"], "Group has no runners"),
        ("echo hi", "missing ':'"),
        (["*:echo 1", "echo 2"], "missing ':'"),
        ("@sync", "cannot start with '@'"),
        (["*:echo 1", 2], "must be strings"),
        (42, "got int"),
        ({"a": "*:echo"}, "got dict"),
    ],
)
def test_validate_runner_rejects_invalid(runner: Any, message: str) -> None:
    with pytest.raises(InvalidRunner, match=message):
        validate_runner(runner)


@pytest.mark.parametrize(
    ("sr", "expected"),
    [
        ("*", False),
        ("*shell", False),
        ("*>", True),
        ("*shell>", True),
        ("*(web)>", True),
        ("*shell(web)>", True),
        ("*(a>b)", False),
        ("app", False),
    ],
)
def test_accepts_extra_args(sr: str, expected: bool) -> None:
    assert accepts_extra_args(sr) is expected


def test_list_process_does_not_mutate_group() -> None:
    group = ["@sync", "*:echo 1", "*:echo 2"]

    result = list_process_and_pre_check_env_vars(group, SETTINGS)

    assert group == ["@sync", "*:echo 1", "*:echo 2"]
    assert [r[0] for r in result] == ["*:echo 1", "*:echo 2"]


def test_find_env_vars() -> None:
    assert find_env_vars("echo {{ A }} {{B}}") == [" A ", "B"]
    assert find_env_vars("echo nothing") == []


def test_check_for_sleep_without_marker() -> None:
    assert check_for_sleep("  echo hi ") == "echo hi"


def test_check_for_sleep_with_marker() -> None:
    assert check_for_sleep("~0~ echo hi") == "echo hi"
