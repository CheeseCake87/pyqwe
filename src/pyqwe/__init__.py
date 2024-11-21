import sys
import threading
import traceback
from functools import partial
from pathlib import Path

from .exceptions import InvalidRunner
from .helpers import _run, _split_runner, Colr
from .parser import ArgumentParser

try:
    import tomllib
except ImportError:
    try:
        import toml as tomllib
    except ImportError:
        raise ImportError("pyqwe requires toml, install it with 'pip install toml'")

__version__ = "1.9.0"

_cwd = Path().cwd()
_known_toml_files = [
    _cwd / "pyqwe.toml",
    _cwd / "pyproject.toml",
]


def _find_toml_file() -> Path:
    for file in _known_toml_files:
        if file.exists():
            return file
    raise FileNotFoundError("pyproject.toml or pyqwe.toml file not found")


_toml_file = _find_toml_file()
_pyproject = tomllib.loads(_toml_file.read_text())

if _toml_file.name == "pyqwe.toml":
    if _pyproject.get("tool", {}).get("pyqwe", {}):
        _qwe = _pyproject.get("tool", {}).get("pyqwe", {})
    else:
        _qwe = _pyproject
else:
    _qwe = _pyproject.get("tool", {}).get("pyqwe", {})


def main():
    pars = ArgumentParser(prog="pyqwe", add_help=False)
    pars.add_argument(
        "--version", "-v", action="version", version=f"pyqwe {__version__}"
    )
    pars.add_argument("--help", "-h", action="help")
    subp = pars.add_subparsers()

    list_parser = subp.add_parser("list")
    list_parser.set_defaults(list=False)

    ls_parser = subp.add_parser("ls")
    ls_parser.set_defaults(list=False)

    for entry, runner in _qwe.items():
        pars.options.append((entry, runner))
        _ = subp.add_parser(entry)
        _.set_defaults(entry=entry, runner=runner)

    args = pars.parse_args()

    if hasattr(args, "list") or hasattr(args, "ls"):
        print("")
        if not pars.options:
            print(f" {Colr.WARNING}No commands found, looking in: {_toml_file.name}{Colr.END}")
        else:
            for option in pars.options:

                try:
                    if type(option[1]) not in [str, list]:
                        raise InvalidRunner()
                except Exception as e:
                    _ = e
                    print(f"💥🏎️⁉️ {Colr.FAIL}Invalid runner: {option}{Colr.END}")
                    print("")
                    sys.exit(0)

                if isinstance(option[1], list):
                    print(f"{Colr.OKCYAN}{option[0]}{Colr.END} {Colr.BOLD}↩︎{Colr.END}  ")
                    for func in option[1]:
                        print(
                            f"  {Colr.BOLD}=>{Colr.END} {Colr.HEADER}{func}{Colr.END}"
                        )
                else:
                    print(
                        f"{Colr.OKCYAN}{option[0]}{Colr.END} "
                        f"{Colr.BOLD}=>{Colr.END} "
                        f"{Colr.HEADER}{option[1]}{Colr.END}"
                    )

        print("")
        sys.exit(0)

    if hasattr(args, "runner"):
        _runner = args.runner

    else:
        if pars.errored:
            sys.exit(0)

        choice, choice_index = pars.print_chooser(_qwe)

        if not choice or not choice.isdigit():
            sys.exit(0)

        if int(choice) == 0:
            sys.exit(0)

        if int(choice) > len(pars.options):
            print(f" {Colr.FAIL}Invalid choice{Colr.END}")
            sys.exit(0)

        _runner = _qwe.get(choice_index[int(choice) - 1])

    try:
        if isinstance(_runner, list):
            sync_ = True if _runner[0] == "@sync" else False
            async_ = True if _runner[0] == "@async" else False
            # async_ is default

            if sync_:
                _runner.pop(0)

                print(f"🏎💨⏱️ {Colr.FAIL}Starting runners in sync{Colr.END}")
                for func in _runner:
                    try:
                        _run(*_split_runner(func), _cwd=_cwd)

                    except KeyboardInterrupt:
                        print(f" 🏁🏎 {Colr.FAIL}Runner stopped{Colr.END}")
                        break

                    except Exception as e:
                        traceback.print_exc()
                        print(f"💥🏎️⁉️ {Colr.FAIL}{e}{Colr.END}")

                print(f" 🏁🏎 {Colr.FAIL}Runners stopped{Colr.END}")
                sys.exit(0)

            if async_:
                _runner.pop(0)

            try:
                print(f"🏎💨🏎💨🏎💨 {Colr.FAIL}Starting runners in async{Colr.END}")
                func_list = []
                threads = []

                for func in _runner:
                    func_list.append(partial(_run, *_split_runner(func), _cwd=_cwd))

                for func in func_list:
                    threads.append(threading.Thread(target=func))

                for thread in threads:
                    thread.start()

                for thread in threads:
                    thread.join()

            except KeyboardInterrupt:
                print(f" 🏁🏎🏎🏎 {Colr.FAIL}Runners stopped{Colr.END}")

            except Exception as e:
                print(f"💥🏎️⁉️ {Colr.FAIL}{e}{Colr.END}")

        else:
            print(f"🏎💨 {Colr.FAIL}Starting runner{Colr.END}")
            _run(*_split_runner(_runner), _cwd=_cwd)

    except KeyboardInterrupt:
        print(f" 🏁🏎 {Colr.FAIL}Runner stopped{Colr.END}")

    except Exception as e:
        traceback.print_exc()
        print(f"💥🏎️⁉️ {Colr.FAIL}{e}{Colr.END}")
