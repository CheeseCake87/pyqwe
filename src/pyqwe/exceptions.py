class PyqweError(Exception):
    """
    An error pyqwe reports as a one line message, exiting with exit_code.
    """

    exit_code = 1


class UsageError(PyqweError):
    """
    The command line was wrong, e.g. an unknown command.
    """

    exit_code = 2


class ConfigError(PyqweError):
    """
    The pyqwe.toml / pyproject.toml file is missing or invalid.
    """


class InvalidRunner(PyqweError):
    """
    A runner string is not something pyqwe can run.
    """


class NotAModuleOrPackage(PyqweError):
    """
    A Python runner points at a module or package that does not exist.
    """


class EnvVarNotFound(PyqweError):
    """
    A {{ VAR }} in a runner is not set.
    """
