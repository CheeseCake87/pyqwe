import importlib.metadata

from .cli import main

__all__ = ["main"]

__version__ = importlib.metadata.version("pyqwe")
