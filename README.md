# 🏎️💨 pyqwe

The Quick Work Environment for Python.

Run commands quickly from the pyproject.toml file.

```bash
pip install pyqwe
```

For `.env` file support using python-dotenv:

```bash
pip install pyqwe[dotenv]
# If zsh install extra using:
pip install 'pyqwe[dotenv]'
```

See [using environment variables](#using-environment-variables) for more information.

## Usage

Add commands to the pyproject.toml file.

```toml
[tool.pyqwe]
flask = "flask_app:run"
say_hello = "*:echo Hello World"
```

You will be able to see what commands you have set in the pyproject.toml file by running:

```bash
pyqwe list
```

### Python commands:

For Python, the commands are structured like (package:module):function

#### Package example:

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

#### Module example:

```text
project/
    app.py
```

```toml
[tool.pyqwe]
flask = "app:run"
```

This command will run the function
`run()` from the `app.py` file.

Now run the pyqwe command:

```bash
pyqwe flask
```

This will start the Flask app.

### *:... commands:

Any command that starts with `*` will be run using subprocess.

For example:

```toml
[tool.pyqwe]
say_hello = "*:echo Hello World"
```

Now running the pyqwe command:

```bash
pyqwe say_hello
```

Will print `Hello World`.

### Run as shell

To run the command as a subprocess shell command, add the `shell` key to the command.

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

This can be used with the `shell` key.

```toml
[tool.pyqwe]
npm_install = "*shell(node_app):npm i"
```

### Using environment variables

To use environment variables in the command, use the `{{ }}` syntax.

```toml
[tool.pyqwe]
talk = "*shell:echo {{MESSAGE}}"
```

Now running the pyqwe command:

```bash
pyqwe talk
```

Will print the value of the `MESSAGE` environment variable.

⚠️ **Note:** The environment variables must be set before running the command.

pyqwe will not look for the `.env` file by default. To enable this, install the `pyqwe-extra-dotenv` package.

```bash
pip install pyqwe-extra-dotenv
```

or

```bash
pip install pyqwe[dotenv]
```

To stop the behavior of looking for the `.env` when using pyqwe, uninstall the `pyqwe-extra-dotenv` package.

```bash
pip uninstall pyqwe-extra-dotenv
```

### Other commands

`pyqwe` `-h` or `--help` will display all the commands set in the pyproject.toml file.

`pyqwe` `__version__` will display the version of pyqwe.
