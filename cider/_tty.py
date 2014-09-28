# -*- coding: utf-8 -*-
import re
import sys

CLEAR = 0
RED = 31
GREEN = 32
YELLOW = 33
BLUE = 34
MAGENTA = 35
WHITE = 39

_prefix_re = re.compile(r"[.:!?>]$")


def error(msg, prefix=None):
    if prefix is None:
        prefix = "Whoops!"
    delimeter = "" if _prefix_re.search(prefix) else ":"
    return "{0}{1} {2}".format(
        underline(prefix, RED),
        delimeter,
        msg
    )


def success(msg, prefix=None):
    if prefix is None:
        prefix = "Success!"
    delimeter = "" if _prefix_re.search(prefix) else ":"
    return "{0}{1} {2}".format(
        underline(prefix, GREEN),
        delimeter,
        msg
    )


def progress(msg, prefix=None):
    if prefix is None:
        prefix = "==>"
    delimeter = "" if _prefix_re.search(prefix) else ":"
    return "{0}{1} {2}".format(
        bold(prefix, BLUE),
        delimeter,
        bold(msg, WHITE)
    )


def debug(msg, prefix=None):
    if prefix is None:
        prefix = "==>"
    delimeter = "" if _prefix_re.search(prefix) else ":"
    return "{0}{1} {2}".format(
        bold(prefix, YELLOW),
        delimeter,
        bold(msg, WHITE)
    )


def puterr(msg, warning=None, prefix=None):
    if warning is None:
        warning = False
    if warning and prefix is None:
        prefix = "Warning"
    sys.stderr.write(error(msg, prefix=prefix) + "\n")


def puts(msg, prefix=None):
    sys.stdout.write(success(msg, prefix=prefix) + "\n")


_debug = debug
def putdebug(msg, debug=None, prefix=None):
    if debug is None:
        debug = False
    if debug:
        sys.stdout.write(_debug(msg, prefix=prefix) + "\n")


def color(msg, num):
    return __escape(msg, "0;{0}".format(num))


def underline(msg, num):
    return __escape(msg, "4;{0}".format(num))


def bold(msg, num):
    return __escape(msg, "1;{0}".format(num))


def __escape(msg, seq):
    fmt = "\033[{0}m"
    return fmt.format(seq) + msg + fmt.format(CLEAR)
