import sys
import threading
from functools import partial
from pathlib import Path

from pyqwe import printer

from .exceptions import InvalidRunner
from .helpers import _find_toml_file, _get_toml, _run, _split_runner, Colr
from .parser import ArgumentParser

__version__ = "2.0.0"

CWD = Path().cwd()
TOML_FILE, QWE = _get_toml(CWD)


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

    for entry, runner in QWE.items():
        pars.options.append((entry, runner))
        _ = subp.add_parser(entry)
        _.set_defaults(entry=entry, runner=runner)

    args = pars.parse_args()

    ####################
    # COMMAND: list, ls
    if hasattr(args, "list") or hasattr(args, "ls"):
        printer.br()

        if not pars.options:
            printer.no_commands_found(TOML_FILE)
        else:
            for option in pars.options:
                try:
                    if type(option[1]) not in [str, list]:
                        raise InvalidRunner()
                except Exception as e:
                    _ = e
                    printer.invalid_runner(option)
                    sys.exit()

                name = option[0]
                value = option[1]

                if isinstance(value, list):
                    printer.option_value_list(name, value)
                else:
                    printer.option_value(name, value)

        printer.br()
        sys.exit()

    ####################
    # COMMAND: <runnner>
    if hasattr(args, "runner"):
        _runner = args.runner

    ####################
    # COMMAND: None
    else:
        if pars.errored:
            # Exit if there are errors
            sys.exit()

        choice, choice_index = pars.print_chooser(QWE)

        # Build a list of choices

        if not choice or not choice.isdigit():
            sys.exit()

        if int(choice) == 0:
            sys.exit()

        if int(choice) > len(pars.options) or int(choice) < 0:
            printer.invalid_choice()
            sys.exit()

        _runner = QWE.get(choice_index[int(choice) - 1])

    ####################
    # If runner is a group
    if isinstance(_runner, list):
        step_ = True if _runner[0] == "@step" else False
        sync_ = True if _runner[0] == "@sync" else False
        async_ = True  # async_ is default

        if step_:  # RUNNERS IN STEP
            async_ = False
            _runner.pop(0)

            printer.starting_step_runners()

            for func in _runner:
                printer.about_to_start_runner(func)

                try:
                    continue_ = input(f"{Colr.WARNING}Continue? [Y/n]: {Colr.END}")

                    if continue_.lower() == "n":
                        printer.runner_skipped()
                        continue

                    printer.starting_runner()

                except KeyboardInterrupt:
                    printer.br()
                    printer.runners_aborted()
                    sys.exit()

                try:
                    _run(*_split_runner(func), _cwd=CWD)

                except KeyboardInterrupt:
                    printer.runner_stopped()

                except Exception as e:
                    printer.crash(e)

                printer.runner_done()

            sys.exit()

        if sync_:  # RUNNERS IN SYNC
            async_ = False
            _runner.pop(0)

            printer.starting_sync_runners()

            for func in _runner:
                try:
                    _run(*_split_runner(func), _cwd=CWD)

                except KeyboardInterrupt:
                    printer.runner_stopped()

                except Exception as e:
                    printer.crash(e)

            printer.runners_stopped()
            sys.exit()

        if async_:
            _runner.pop(0)

            printer.starting_async_runners()

            try:
                func_list = []
                threads = []

                for func in _runner:
                    func_list.append(partial(_run, *_split_runner(func), _cwd=CWD))

                for func in func_list:
                    threads.append(threading.Thread(target=func))

                for thread in threads:
                    thread.start()

                for thread in threads:
                    thread.join()

            except KeyboardInterrupt:
                printer.runners_stopped()
                sys.exit()

            except Exception as e:
                printer.crash(e)
                sys.exit()

        # Exit list of runners
        sys.exit()

    ####################
    # If runner is a single command
    else:
        printer.starting_runner()

        try:
            _run(*_split_runner(_runner), _cwd=CWD)

        except KeyboardInterrupt:
            printer.runner_stopped()
            sys.exit()

        except Exception as e:
            printer.crash(e)
