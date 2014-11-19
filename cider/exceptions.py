import os


class CiderException(Exception):
    def __init__(self, message, exit_code=None):
        if exit_code is None:
            exit_code = 1
        Exception.__init__(self, message)
        self.exit_code = exit_code


class ParserError(CiderException):
    def __init__(self, message, path, exit_code=None):
        is_json = os.path.splitext(path)[1] == ".json"
        CiderException.__init__(self, message, exit_code)
        self.filepath = path
        self.filetype = "JSON" if is_json else "YAML"


class UnsupportedOSError(CiderException):
    def __init__(self, message, macos_version, exit_code=None):
        CiderException.__init__(self, message, exit_code)
        self.macos_version = macos_version


class BrewMissingError(CiderException):
    def __init__(self, message, url, exit_code=None):
        CiderException.__init__(self, message, exit_code)
        self.url = url


class XcodeMissingError(CiderException):
    pass


class SymlinkError(CiderException):
    pass


class AppMissingError(CiderException):
    pass


class StowError(CiderException):
    pass
