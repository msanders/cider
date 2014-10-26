# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from . import _tty as tty
from .exceptions import JSONError
from subprocess import CalledProcessError
import click
import copy
import errno
import json
import os
import pwd
import subprocess

JSONDecodeError = ValueError


class Brew(object):
    def __init__(self, cask=None, debug=None, verbose=None):
        self.cask = cask if cask is not None else False
        self.debug = debug if debug is not None else False
        self.verbose = verbose if verbose is not None else False

    def __spawn(self, cmd, cmdargs, prompt=None, check_output=None):
        check_output = check_output if check_output is not None else False

        args = ["brew"] + (["cask"] if self.cask else [])
        args += [cmd] + cmdargs

        # `brew ls` doesn't seem to like these flags.
        if cmd != "ls":
            args += (["--debug"] if self.debug else [])
            args += (["--verbose"] if self.verbose else [])

        try:
            return spawn(args, debug=self.debug, check_output=check_output)
        except CalledProcessError as e:
            if not prompt or not click.confirm(prompt):
                raise e

    def __assert_no_cask(self, cmd):
        assert not self.cask, "no such command: `brew cask {0}`".format(cmd)

    def safe_install(self, formula):
        prompt = "Failed to install {0}. Continue? [y/N]".format(formula)
        return self.__spawn("install", formula.split(" "), prompt)

    def install(self, *formulas, **kwargs):
        formulas = list(formulas) or []
        force = kwargs.get("force", False)

        args = formulas + (["--force"] if force else [])
        return self.__spawn("install", args)

    def rm(self, *formulas, **kwargs):
        formulas = list(formulas) or []
        force = kwargs.get("force", False)

        args = formulas + (["--force"] if force else [])
        cmd = "rm" if not self.cask else "zap"
        return self.__spawn(cmd, args)

    def tap(self, tap):
        self.__assert_no_cask(__name__)
        return self.__spawn("tap", [tap] if tap is not None else [])

    def untap(self, tap):
        self.__assert_no_cask(__name__)
        return self.__spawn("untap", [tap])

    def ls(self):
        return self.__spawn(
            "ls", ["-1"], check_output=True
        ).strip().split("\n")

    def uses(self, formula):
        args = ["--installed", "--recursive", formula]
        return self.__spawn(
            "uses", args, check_output=True
        ).strip().split("\n")


class Defaults(object):
    def __init__(self, debug=None):
        self.debug = debug if debug is not None else False

    def write(self, domain, key, value, force=None):
        force = force if force is not None else False

        args = ["defaults", "write"] + (["-f"] if force else [])
        args += [domain, key, self.key_type(value), str(value)]
        return spawn(args, debug=self.debug)

    def delete(self, domain, key):
        return spawn(["defaults", "delete", domain, key], debug=self.debug)

    @staticmethod
    def key_type(value):
        key_types = {
            bool: "-bool",
            float: "-float",
            int: "-int"
        }

        return next(
            (k for t, k in key_types.items() if isinstance(value, t)),
            "-string"
        )


def spawn(args, **kwargs):
    check_call = kwargs.get("check_call", True)
    check_output = kwargs.get("check_output", False)
    debug = kwargs.get("debug", False)

    kwarg_params = ["check_call", "check_output", "debug"]
    params = dict((k, v) for (k, v) in kwargs.items()
                  if k not in kwarg_params)

    tty.putdebug(" ".join(args), debug)

    if check_output:
        return subprocess.check_output(args, **params)
    elif check_call:
        return subprocess.check_call(args, **params)
    else:
        return subprocess.call(args, **params)


def curl(url, path):
    return spawn(["curl", "-L", url, "-o", path, "--progress-bar"])


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST or not os.path.isdir(path):
            raise


def collapseuser(path):
    home_dir = os.environ.get("HOME", pwd.getpwuid(os.getuid()).pw_dir)
    if os.path.samefile(home_dir, commonpath([path, home_dir])):
        return os.path.join("~", os.path.relpath(path, home_dir))
    return path


def isdirname(path):
    return path.endswith(os.path.sep) or path == "~"


# os.path.commonprefix doesn't behave as you'd expect - see
# https://stackoverflow.com/a/21499568/176049
def commonpath(paths):
    paths = (os.path.dirname(p) if not os.path.isdir(p) else p for p in paths)
    norm_paths = [os.path.abspath(p) + os.path.sep for p in paths]
    return os.path.dirname(os.path.commonprefix(norm_paths))


def read_json(path, fallback=None):
    try:
        with open(path, "r") as f:
            return json.loads(f.read() or "{}")
    except IOError as e:
        if fallback is not None and e.errno == errno.ENOENT:
            return fallback

        raise e
    except JSONDecodeError as e:
        raise JSONError(e, path)


def modify_json(path, transform):
    contents = read_json(path, {})
    with open(path, "w") as f:
        old_contents = contents
        contents = transform(copy.deepcopy(contents))
        changed = bool(old_contents != contents)

        if changed:
            json.dump(
                contents,
                f,
                indent=4,
                sort_keys=True,
                separators=(',', ': ')
            )

        return changed


def write_json(path, contents):
    with open(path, "w") as f:
        json.dump(
            contents, f, indent=4, sort_keys=True, separators=(',', ': ')
        )
