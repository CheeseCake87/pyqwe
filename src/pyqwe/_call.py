import importlib
import sys


def main(argv: list[str]) -> int:
    root, module_name, function_name = argv

    # The project comes first
    sys.path.insert(0, root)

    module = importlib.import_module(module_name)
    function = getattr(module, function_name, None)

    if function is None:
        print(
            f"Error: {function_name} function not found in {module_name}",
            file=sys.stderr,
        )
        return 1

    if not callable(function):
        print(
            f"Error: {function_name} is not a function in {module_name}",
            file=sys.stderr,
        )
        return 1

    try:
        function()
    except KeyboardInterrupt:
        return 130

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
