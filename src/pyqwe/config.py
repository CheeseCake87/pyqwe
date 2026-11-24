import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .exceptions import ConfigError

SETTINGS = ("__clear_terminal__", "__env_ignore__", "__env_files__")
SECTION_SETTINGS = ("__header__",)
COMMAND_TABLE_KEYS = ("run", "help")

# Command names cannot start with '-' (they would look like options)
_COMMAND_NAME = re.compile(r"^[^\s-]\S*$")


@dataclass(frozen=True)
class Command:
    name: str
    runner: str | list[str]
    help: str | None = None
    section: str | None = None


@dataclass(frozen=True)
class Config:
    file: Path
    commands: dict[str, Command] = field(default_factory=dict)
    clear_terminal: bool = False
    env_ignore: bool = False
    env_files: tuple[str, ...] = ()

    @property
    def root(self) -> Path:
        return self.file.parent


def find_toml_file(cwd: Path) -> Path:
    for file in (cwd / "pyqwe.toml", cwd / "pyproject.toml"):
        if file.is_file():
            return file

    raise ConfigError(f"No pyqwe.toml or pyproject.toml file found in {cwd}")


def load_toml(file: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(file.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Could not read {file.name}: {e}") from e


def get_pyqwe_table(file: Path, data: dict[str, Any]) -> dict[str, Any]:
    """
    pyproject.toml uses [tool.pyqwe], pyqwe.toml can use either
    [tool.pyqwe] or the top level of the file.
    """
    tool_pyqwe = data.get("tool", {}).get("pyqwe", {})

    if file.name == "pyqwe.toml" and not tool_pyqwe:
        return data

    if not isinstance(tool_pyqwe, dict):
        raise ConfigError("[tool.pyqwe] must be a table")

    return tool_pyqwe


def load_config(cwd: Path) -> Config:
    file = find_toml_file(cwd)
    return parse_config(file, get_pyqwe_table(file, load_toml(file)))


def _is_setting(key: str) -> bool:
    return key.startswith("__") and key.endswith("__")


def _parse_command(name: str, value: Any, section: str | None) -> Command:
    if not _COMMAND_NAME.match(name):
        raise ConfigError(
            f"Invalid command name {name!r}, names cannot contain spaces "
            "or start with '-'"
        )

    help_ = None

    if isinstance(value, dict):
        unknown = set(value) - set(COMMAND_TABLE_KEYS)
        if unknown:
            raise ConfigError(
                f"Unknown key(s) {', '.join(sorted(unknown))} in command {name!r}, "
                f"expected {', '.join(COMMAND_TABLE_KEYS)}"
            )
        help_ = value.get("help")
        if help_ is not None and not isinstance(help_, str):
            raise ConfigError(f"'help' for command {name!r} must be a string")
        value = value["run"]

    if isinstance(value, str):
        return Command(name, value, help_, section)

    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return Command(name, value, help_, section)

    raise ConfigError(
        f"Invalid runner for command {name!r}: expected a string, a list of "
        f"strings or a table with 'run', got {value!r}"
    )


def parse_config(file: Path, table: dict[str, Any]) -> Config:
    settings: dict[str, Any] = {}
    commands: dict[str, Command] = {}

    def _add(command: Command) -> None:
        if command.name in commands:
            raise ConfigError(f"Command {command.name!r} is defined more than once")
        commands[command.name] = command

    for key, value in table.items():
        if _is_setting(key):
            if key not in SETTINGS:
                raise ConfigError(
                    f"Unknown setting {key!r}, expected one of {', '.join(SETTINGS)}"
                )
            settings[key] = value
            continue

        # A sub-table without 'run' is a section of commands
        if isinstance(value, dict) and "run" not in value:
            header = value.get("__header__", key)
            if not isinstance(header, str):
                raise ConfigError(f"__header__ in section {key!r} must be a string")

            for sub_key, sub_value in value.items():
                if _is_setting(sub_key):
                    if sub_key not in SECTION_SETTINGS:
                        raise ConfigError(
                            f"Unknown section setting {sub_key!r} in section "
                            f"{key!r}, expected one of {', '.join(SECTION_SETTINGS)}"
                        )
                    continue
                if isinstance(sub_value, dict) and "run" not in sub_value:
                    raise ConfigError(
                        f"Sections cannot be nested: {key!r} contains {sub_key!r}"
                    )
                _add(_parse_command(sub_key, sub_value, header))
            continue

        _add(_parse_command(key, value, None))

    clear_terminal = settings.get("__clear_terminal__", False)
    env_ignore = settings.get("__env_ignore__", False)
    env_files = settings.get("__env_files__", [])

    if not isinstance(clear_terminal, bool):
        raise ConfigError("__clear_terminal__ must be true or false")
    if not isinstance(env_ignore, bool):
        raise ConfigError("__env_ignore__ must be true or false")
    if not isinstance(env_files, list) or not all(
        isinstance(f, str) for f in env_files
    ):
        raise ConfigError("__env_files__ must be a list of file names")

    return Config(
        file=file,
        commands=commands,
        clear_terminal=clear_terminal,
        env_ignore=env_ignore,
        env_files=tuple(env_files),
    )


def load_env_files(config: Config) -> bool:
    if config.env_ignore:
        return False

    try:
        from dotenv import load_dotenv  # type: ignore[import-not-found,unused-ignore]
    except ImportError:
        if config.env_files:
            raise ConfigError(
                "__env_files__ is set but python-dotenv is not installed, "
                "install it with 'pip install python-dotenv'"
            ) from None
        return False

    if config.env_files:
        files = [config.root / f for f in config.env_files]
    else:
        files = [f for f in [config.root / ".env"] if f.is_file()]

    for file in files:
        if not file.is_file():
            raise ConfigError(f"Environment file not found: {file}")
        load_dotenv(file)

    return True
