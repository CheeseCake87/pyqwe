class NotAModuleOrPackage(Exception):
    pass


class FunctionNotFound(Exception):
    pass


class NotAFunction(Exception):
    pass


__all__ = ["NotAModuleOrPackage", "FunctionNotFound", "NotAFunction"]
