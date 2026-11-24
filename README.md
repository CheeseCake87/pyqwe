# 🏎️💨 pyqwe

The Quick Work Environment for Python.

[![PyPI version](https://img.shields.io/pypi/v/pyqwe)](https://pypi.org/project/pyqwe/)
[![License](https://img.shields.io/github/license/CheeseCake87/pyqwe)](https://raw.githubusercontent.com/CheeseCake87/pyqwe/main/LICENSE)

Run commands quickly from the pyproject.toml (or pyqwe.toml) file.

```bash
pip install pyqwe
```

pyqwe requires Python 3.12 or newer.

---

<!-- TOC -->
* [🏎️💨 pyqwe](#-pyqwe)
  * [Usage](#usage)
  * [Describing commands](#describing-commands)
  * [Sections](#sections)
  * [Python commands](#python-commands)
    * [Package example](#package-example)
    * [Module example](#module-example)
  * [*:... commands (terminal)](#-commands-terminal)
    * [Run as shell](#run-as-shell)
    * [Change the working directory](#change-the-working-directory)
    * [Passing extra arguments](#passing-extra-arguments)
  * [Grouped commands](#grouped-commands)
  * [Waiting before starting a runner](#waiting-before-starting-a-runner)
  * [Exit codes](#exit-codes)
  * [Using environment variables](#using-environment-variables)
  * [Clearing the terminal setting](#clearing-the-terminal-setting)
  * [Dry run](#dry-run)
  * [Shell completion](#shell-completion)
  * [Colours](#colours)
  * [Other commands](#other-commands)
<!-- TOC -->

## Usage

Add commands to the pyproject.toml or pyqwe.toml file.

🚨**NOTE** - If you have both a pyproject.toml and a pyqwe.toml file, the pyqwe.toml
file will be used and the pyproject.toml file will be ignored.

```toml
[tool.pyqwe]
flask = "flask_app:run"
say_hello = "*:echo Hello World"
```

If you're using a pyqwe.toml file you can drop the `[tool.pyqwe]`

```toml
flask = "flask_app:run"
say_hello = "*:echo Hello World"
```

To see information on the available commands in the toml file you can run:

```bash
qwe list
# or
qwe ls
# or
qwe --list
# or
qwe -l
```

`qwe` is a shorter alias for `pyqwe`, every example here works with either.

If you define your own command called `list` or `ls`, yours is run instead,
and `qwe --list` still lists your commands.

You can run the commands by using the command name:

```bash
qwe flask
```

Running `qwe` without any option or command will show all available
commands in a menu you can choose from.

```bash
qwe
```

```text
  0...Exit
  1...flask
  2...say_hello
Select a command to run [0]:
```

Choosing `1` will run the `flask` command.

## Describing commands

A command can be a table with `run` and `help`, the help text is shown in
`qwe ls`, the menu, and [shell completion](#shell-completion) in zsh and fish:

```toml
[tool.pyqwe]
test = { run = "*:pytest", help = "Run the tests" }
dev = { run = ["*:npm run dev", "app:run"], help = "Start the dev servers" }
```

## Sections

A sub-table of commands is shown as its own section in `qwe ls` and the
menu. Use `__header__` to give it a title, otherwise the table name is used:

```toml
[tool.pyqwe]
test = "*:pytest"

[tool.pyqwe.js]
__header__ = "JavaScript"
js_install = "*(js_app):npm install"
js_dev = "*(js_app):npm run dev"
```

Commands in sections are run by their name, `qwe js_install`, so names must
be unique across all sections.

## Python commands

For Python, the commands are structured like (package &/ module):function

### Package example

```text
project/
    flask_app/
        __init__.py
```

```toml
[tool.pyqwe]
flask = "flask_app:run"
```

This command will run the function
`run()` from the `__init__.py` file in the `flask_app` package.

### Module example

```text
project/
    app.py
```

```toml
[tool.pyqwe]
flask = "app:run"
```

This command will run the function
`run()` from the `app.py` file. Writing `app.py:run` works too.

Modules inside packages use dots, `my_package.inside:run` will run the
function `run()` from `my_package/inside.py`. Modules are imported by their
full name relative to the project folder, so relative imports work, and a
module in your project takes priority over an installed package with the
same name.

Each Python command runs in its own process, using the same Python that
pyqwe is installed in. This means Ctrl+C stops it, it can set the exit code
with `sys.exit()`, and Python commands in a group do not share imports.

Now run the pyqwe command:

```bash
qwe flask
```

This will start the Flask app.

## *:... commands (terminal)

Any command that starts with `*` will be run using subprocess.

For example:

```toml
[tool.pyqwe]
say_hello = "*:echo Hello World"
```

Now running the pyqwe command:

```bash
qwe say_hello
```

Will print `Hello World`.

### Run as shell

To run the command as a subprocess shell command, add the `shell` key to the
command.

On Windows, terminal commands always run through the shell, so that commands
like `npm` and shell built-ins like `echo` can be found.

```toml
[tool.pyqwe]
say_hello = "*shell:echo Hello World"
```

### Change the working directory

You can change the working directory of a subprocess by adding the folder
within parentheses to the command, `(node_app)` for example.

**The folder must be relative** to the pyproject.toml file.

**Absolute paths are not supported**.

**Moving up directories is not supported**, `../node_app` for example.

```toml
[tool.pyqwe]
npm_install = "*(node_app):npm install"
```

The `shell` key is still available when changing the directory.

```toml
[tool.pyqwe]
npm_install = "*shell(node_app):npm i"
```

### Passing extra arguments

Adding `>` to a terminal command (`*>:...`) allows it to take extra
arguments. Anything given after the command name is appended to the
end of the command.

```toml
[tool.pyqwe]
uv = "*>:uv run --env-file .env -- uv"
```

```bash
qwe uv add python-dotenv
```

This will run `uv run --env-file .env -- uv add python-dotenv`.

`>` can be combined with `shell` and the working directory,
`*shell>:...`, `*(node_app)>:...` or `*shell(node_app)>:...`.

The parts must be in this order: `*`, then `shell`, then `(folder)`, then
`>`. Anything else, `*sh:...` or `*>(node_app):...` for example, is reported
as an invalid runner before anything runs.

Passing extra arguments to a command that is not marked with `>` will
raise an error.

## Grouped commands

You can group commands together in a list to have one pyqwe command run
multiple commands.

Grouped commands can also be run in Step, Sync, or Async mode. Async being the
default.

This will run the commands in the group in sequence, pausing for confirmation
between each command:

```toml
[tool.pyqwe]
group = [
    "@step",
    "*:echo 'Hello, World! 1'",
    "*:echo 'Hello, World! 2'",
    "*:echo 'Hello, World! 3'"
]
```

This will run the commands in the group in sequence, one after the other,
stopping at the first command that fails:

```toml
[tool.pyqwe]
group = [
    "@sync",
    "*:echo 'Hello, World! 1'",
    "*:echo 'Hello, World! 2'",
    "*:echo 'Hello, World! 3'"
]
```

This will run the commands in the group in parallel:

```toml
[tool.pyqwe]
group = [
    "@async",
    "*:echo 'Hello, World! 1'",
    "*:echo 'Hello, World! 2'",
    "*:echo 'Hello, World! 3'"
]
```

Of course, you can leave out the `@step`, `@sync` or `@async` to use the
default async mode. Any other `@` mode, `@synch` for example, is reported as
an error.

For example, this will also run the commands in the group in parallel:

```toml
[tool.pyqwe]
group = [
    "*:echo 'Hello, World! 1'",
    "*:echo 'Hello, World! 2'",
    "*:echo 'Hello, World! 3'"
]
```

## Waiting before starting a runner

Sometimes you might need to have a runner wait before starting. This might
be the case if you have a group of runners in async mode but one runner
connects to another.

You can tell a runner to sleep for a number of seconds by using the sleep
for marker:

```toml
[tool.pyqwe]
group = [
    "@async",
    "*:~10~ echo 'Hello, World! 1'",
    "*:echo 'Hello, World! 2'",
    "*:echo 'Hello, World! 3'"
]
```

This also works on module runs:

```toml
[tool.pyqwe]
flask = "~10~ flask_app:run"
```

Each of the examples above will sleep for 10 seconds before the runner will
start.

## Exit codes

pyqwe exits with the exit code of the command it ran, so it can be used in
scripts and CI:

```bash
qwe test && qwe deploy
```

| Situation                                             | Exit code              |
|-------------------------------------------------------|------------------------|
| The command succeeded                                 | `0`                    |
| A terminal command failed                             | The command's own code |
| A terminal command was not found                      | `127`                  |
| A Python function raised an error                     | `1`                    |
| The command is invalid, or the menu choice is invalid | `1`                    |
| Unknown command, or extra arguments given without `>` | `2`                    |
| Stopped with Ctrl+C                                   | `130`                  |

Error messages are printed to stderr.

For grouped commands:

- `@sync` stops at the first command that fails and exits with its code.
  Pressing Ctrl+C stops the current command and moves on to the next.
- `@step` carries on, since you choose whether to run each command, and
  exits with the code of the first command that failed.
- `@async` waits for all commands and exits with the code of the first
  command that failed.

## Using environment variables

To use environment variables in the command, use the `{{ }}`
markers:

```toml
[tool.pyqwe]
talk = "*shell:echo {{ MESSAGE }}"
```

pyqwe fills in the values before running anything. If a variable is not set,
pyqwe reports it and runs nothing.

Variables already set in your environment always work. To also load them
from a `.env` file, install `python-dotenv`:

```bash
pip install python-dotenv
```

pyqwe then loads the `.env` file in the project folder, if there is one. To
load other files, set `__env_files__`:

```toml
[tool.pyqwe]
__env_files__ = [".env", ".env.local"]
talk = "*shell:echo {{ MESSAGE }}"
```

Every file listed in `__env_files__` must exist, and `__env_files__` needs
`python-dotenv` to be installed. Values already set in your environment are
not overwritten.

To turn off everything to do with environment variables, set
`__env_ignore__` to `true`:

```toml
[tool.pyqwe]
__env_ignore__ = true
talk = "*shell:echo {{ MESSAGE }}"
```

No `.env` files are loaded, and `{{ MESSAGE }}` is passed to the command
as it is.

## Clearing the terminal setting

Setting the `__clear_terminal__` setting option to true will clear the
terminal before a command runs, or before the menu is shown. It does nothing
for `--help`, `--list`, `--dry-run` or errors, and nothing when the output
is not a terminal. Results may vary between terminals and OS platforms.

This option is set to false by default.

```toml
[tool.pyqwe]
__clear_terminal__ = true
talk = "*shell:echo {{MESSAGE}}"
```

## Dry run

`--dry-run` (or `-n`) shows what a command would run, without running it.
Environment variables and extra arguments are filled in, so it is a good way
to check a command:

```bash
qwe --dry-run deploy
```

```text
deploy (@sync) would run:
  => python app.build:run
  => (after 5s) (in web) npm run deploy --prod
```

## Shell completion

pyqwe can complete command names and options in bash, zsh and fish. Add one
of these to your shell's startup file:

```bash
# ~/.bashrc
eval "$(qwe --completion bash)"

# ~/.zshrc, after compinit
eval "$(qwe --completion zsh)"
```

```fish
# ~/.config/fish/config.fish
qwe --completion fish | source
```

Completion works for both `qwe` and `pyqwe`, using the commands of the
project in the current folder. zsh and fish also show each command's `help`
text next to its name:

```text
$ qwe <tab>
build       -- Build the package
db:migrate  -- Run the database migrations
test
```

Options such as `--list` and `--dry-run` are completed before the command
name. Everything after the command name belongs to the command, so the shell
completes file names there instead.

In bash, command names containing `:` (like `db:migrate`) complete correctly
when the [bash-completion](https://github.com/scop/bash-completion) package is
installed, which most Linux distributions and Homebrew's bash include.

## Colours

pyqwe uses colour and emoji when printing to a terminal, and plain text when
the output is piped or redirected. Set `NO_COLOR=1` to always turn colour
off, or `FORCE_COLOR=1` to always turn it on.

## Other commands

| Option                         | Description                                        |
|--------------------------------|----------------------------------------------------|
| `-l`, `--list`                 | List all commands                                  |
| `-n`, `--dry-run`              | Show what a command would run, without running it  |
| `--completion {bash,zsh,fish}` | Print a shell completion script                    |
| `-h`, `--help`                 | Show the help message                              |
| `-v`, `--version`              | Show the version                                   |

Options go before the command name. Anything after the command name is passed
to the command, see [Passing extra arguments](#passing-extra-arguments).
