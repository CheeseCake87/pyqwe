# 🏎️💨 pyqwe

The Quick Work Environment for Python.

Run commands quickly from the pyproject.toml file.

`pip install pyqwe`

## Usage

Add commands to the pyproject.toml file.

```toml
[tool.pyqwe]
flask = "flask_app:run"
say_hello = "*:echo Hello World"
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

Now run the qwe command:

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

### Other commands

`pyqwe` `-h` or `--help` will display all the commands set in the pyproject.toml file.

`pyqwe` `__version__` will display the version of qwe.
