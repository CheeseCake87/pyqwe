import sys
import threading
from functools import partial
from pathlib import Path

from pyqwe import printer
from .exceptions import InvalidRunner, EnvVarNotFound
from .helpers import (
    find_toml_file,
    get_toml,
    try_dotenv_import,
    process_and_pre_check_env_vars,
    run_clear,
    run,
    split_runner,
    Colr,
)
from .parser import ArgumentParser

__version__ = "3.1.1"

CWD = Path().cwd()
TOML_FILE, QWE = get_toml(CWD)


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

    clear_terminal = QWE.get("__clear_terminal__", False)
    env_ignore = QWE.get("__env_ignore__", False)
    env_marker_start = "{{"
    env_marker_end = "}}"
    env_files = QWE.get("__env_files__", [])
    if not isinstance(env_ignore, bool):
        raise ValueError("__env_ignore__ must be a boolean")
    if not isinstance(clear_terminal, bool):
        raise ValueError("__clear_terminal__ must be a boolean")
    if not isinstance(env_files, list):
        raise ValueError("__env_files__ must be a list")

    qwe_copy = QWE.copy()

    for key, value in qwe_copy.items():
        if key.startswith("__") and key.endswith("__"):
            del QWE[key]

    settings = {
        "clear_terminal": clear_terminal,
        "env_ignore": env_ignore,
        "env_marker_start": env_marker_start,
        "env_marker_end": env_marker_end,
        "extra_dotenv": try_dotenv_import(CWD, env_files),
    }

    if settings["clear_terminal"]:
        run_clear(_cwd=CWD)

    for entry, entry_runner in QWE.items():
        pars.options.append((entry, entry_runner))
        _ = subp.add_parser(entry)
        _.set_defaults(entry=entry, runner=entry_runner)

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
        runner = args.runner

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

        runner = QWE.get(choice_index[int(choice) - 1])

    ####################
    # If runner is a group
    if isinstance(runner, list):
        step_ = True if runner[0] == "@step" else False
        sync_ = True if runner[0] == "@sync" else False
        async_ = True  # async_ is default

        extracted_runners = process_and_pre_check_env_vars(runner, settings)

        # Fail if any environment variables are not found in the list of runners
        all_env_vars_not_found = []
        for extracted in extracted_runners:
            _, _, _, env_vars_not_found = extracted
            all_env_vars_not_found.extend(env_vars_not_found)

        if all_env_vars_not_found:
            printer.error_()
            raise EnvVarNotFound(
                f"Environment variables not found: {', '.join(all_env_vars_not_found)}"
            )

        if step_:  # RUNNERS IN STEP
            async_ = False

            printer.starting_step_runners()

            for extracted in extracted_runners:
                extracted_runner, sr, er, _ = extracted

                printer.about_to_start_runner(extracted_runner)

                try:
                    continue_ = input(f"{Colr.WARNING}Continue? [Y/n]: {Colr.END}")

                    if continue_.lower() == "n":
                        printer.runner_skipped()
                        continue

                except KeyboardInterrupt:
                    printer.br()
                    printer.runners_aborted()
                    sys.exit()

                try:
                    run(sr, er, _cwd=CWD, _settings=settings)

                except KeyboardInterrupt:
                    printer.runner_stopped()

                except Exception as e:
                    printer.crash(e)

                printer.runner_done()

            sys.exit()

        if sync_:  # RUNNERS IN SYNC
            async_ = False

            printer.starting_sync_runners()

            for extracted in extracted_runners:
                _, sr, er, _ = extracted

                try:
                    run(sr, er, _cwd=CWD, _settings=settings)

                except KeyboardInterrupt:
                    printer.runner_stopped()

                except Exception as e:
                    printer.crash(e)

            printer.runners_stopped()
            sys.exit()

        if async_:
            printer.starting_async_runners()

            try:
                func_list = []
                threads = []

                for extracted in extracted_runners:
                    _, sr, er, _ = extracted

                    func_list.append(partial(run, sr, er, _cwd=CWD, _settings=settings))

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
    if isinstance(runner, str):
        runner, sr, er, env_vars_not_found = process_and_pre_check_env_vars(
            runner, settings
        )

        if env_vars_not_found:
            printer.error_()
            raise EnvVarNotFound(
                f"Environment variables not found: {', '.join(env_vars_not_found)}"
            )

        try:
            run(sr, er, _cwd=CWD, _settings=settings)

        except KeyboardInterrupt:
            printer.runner_stopped()
            sys.exit()

        except Exception as e:
            printer.crash(e)

    else:
        ValueError(
            f"Runner {runner} is not a valid type. Must be a string or list[string]."
        )
        sys.exit()
