# 🏎️💨 pyqwe

The Quick Work Environment.

Run commands quickly from the pyproject.toml file.

`pip install pyqwe`

## Usage

Add commands to the pyproject.toml file.

```toml
[tool.pyqwe]
flask = "flask_app:run"
say_hello = "*cmd:echo Hello World"
```

### Python commands:

For Python, the commands are structured like (package:module):function

#### Package example:

```text
project/
    flask_app/
        __init__.py
```

The following command will run the function
`run` from the `__init__.py` file in the `flask_app` package.

`flask = "flask_app:run"`

#### Module example:

```text
project/
    app.py
```

The following command will run the function
`run` from the `app.py` file.

`flask = "app:run"`

Now run the qwe command:

`qwe flask`

and this will start the Flask app.

### CMD labeled commands:

And command that is labeled with `*cmd` will be ran using subprocess.

`say_hello = "*cmd:echo Hello World"`

Now run the qwe command:

`qwe say_hello`

and this will print `Hello World`.

#### Run as shell

To run the command as a subprocess shell command, add the `shell` key to the command.

`say_hello = "*cmd-shell:echo Hello World"`

### Other commands

`-h` or `--help` will display all the commands set in the pyproject.toml file.
`__version__` will display the version of qwe.
