from pathlib import Path
from typing import Any

import pytest

from pyqwe.config import (
    Command,
    get_pyqwe_table,
    load_config,
    parse_config,
)
from pyqwe.exceptions import ConfigError

FILE = Path("pyqwe.toml")


def test_commands_and_settings() -> None:
    config = parse_config(
        FILE,
        {
            "__clear_terminal__": True,
            "__env_files__": [".env.local"],
            "plain": "*:echo",
            "group": ["@sync", "*:echo"],
            "described": {"run": "*:pytest", "help": "Run the tests"},
        },
    )

    assert config.clear_terminal is True
    assert config.env_ignore is False
    assert config.env_files == (".env.local",)
    assert config.commands == {
        "plain": Command("plain", "*:echo"),
        "group": Command("group", ["@sync", "*:echo"]),
        "described": Command("described", "*:pytest", "Run the tests"),
    }


def test_sections() -> None:
    config = parse_config(
        FILE,
        {
            "top": "*:echo",
            "js": {"__header__": "JavaScript", "install": "*(js):npm i"},
            "tools": {"fmt": {"run": "*:ruff format", "help": "Format"}},
        },
    )

    assert config.commands["top"].section is None
    assert config.commands["install"].section == "JavaScript"
    assert config.commands["fmt"] == Command("fmt", "*:ruff format", "Format", "tools")


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ({"__unknown__": 1}, "Unknown setting '__unknown__'"),
        ({"__clear_terminal__": "yes"}, "__clear_terminal__ must be true or false"),
        ({"__env_ignore__": 1}, "__env_ignore__ must be true or false"),
        ({"__env_files__": ".env"}, "__env_files__ must be a list"),
        ({"__env_files__": [1]}, "__env_files__ must be a list"),
        ({"bad": 42}, "Invalid runner for command 'bad'"),
        ({"bad": ["*:echo", 1]}, "Invalid runner for command 'bad'"),
        ({"bad": {"run": "*:echo", "hlep": "x"}}, "Unknown key\\(s\\) hlep"),
        ({"bad": {"run": "*:echo", "help": 1}}, "'help' for command 'bad'"),
        ({"-bad": "*:echo"}, "Invalid command name '-bad'"),
        ({"bad name": "*:echo"}, "Invalid command name 'bad name'"),
        ({"a": "*:echo", "s": {"a": "*:echo"}}, "'a' is defined more than once"),
        ({"s": {"inner": {"x": "*:echo"}}}, "Sections cannot be nested"),
        ({"s": {"__nope__": "x"}}, "Unknown section setting '__nope__'"),
        ({"s": {"__header__": 1}}, "__header__ in section 's' must be a string"),
    ],
)
def test_invalid_config(table: dict[str, Any], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        parse_config(FILE, table)


def test_pyproject_uses_tool_pyqwe() -> None:
    data = {"project": {"name": "x"}, "tool": {"pyqwe": {"a": "*:echo"}}}

    assert get_pyqwe_table(Path("pyproject.toml"), data) == {"a": "*:echo"}
    assert get_pyqwe_table(Path("pyproject.toml"), {"project": {}}) == {}


def test_pyqwe_toml_can_use_top_level_or_tool_pyqwe() -> None:
    assert get_pyqwe_table(FILE, {"a": "*:echo"}) == {"a": "*:echo"}
    assert get_pyqwe_table(FILE, {"tool": {"pyqwe": {"b": "*:echo"}}}) == {
        "b": "*:echo"
    }


def test_load_config_prefers_pyqwe_toml(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[tool.pyqwe]\nfrom_pyproject = '*:echo'\n"
    )
    (tmp_path / "pyqwe.toml").write_text("from_pyqwe = '*:echo'\n")

    config = load_config(tmp_path)

    assert list(config.commands) == ["from_pyqwe"]
    assert config.root == tmp_path


def test_load_config_without_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="No pyqwe.toml or pyproject.toml"):
        load_config(tmp_path)
