# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from subprocess import CalledProcessError
from . import _tty as tty
import subprocess
import click


class Brew(object):
    def __init__(self, cask=None, debug=None, verbose=None):
        self.cask = cask if cask is not None else False
        self.debug = debug if debug is not None else False
        self.verbose = verbose if verbose is not None else False

    def _spawn(self, cmd, cmdargs, prompt=None, check_output=None):
        check_output = check_output if check_output is not None else False

        args = ["brew"] + (["cask"] if self.cask else [])
        args += [cmd] + cmdargs

        # `brew ls` doesn't seem to like these flags.
        if cmd != "ls" or self.cask:
            args += (["--debug"] if self.debug else [])
            args += (["--verbose"] if self.verbose else [])

        try:
            return spawn(args, debug=self.debug, check_output=check_output)
        except CalledProcessError as e:
            if not prompt or click.confirm(prompt):
                raise e

    def safe_install(self, formula):
        prompt = "Failed to install {0}. Continue? [y/N]".format(formula)
        return self._spawn("install", [formula], prompt)

    def install(self, *formulas, **kwargs):
        formulas = list(formulas) or []
        force = kwargs.get("force", False)

        args = formulas + (["--force"] if force else [])
        return self._spawn("install", args)

    def rm(self, *formulas, **kwargs):
        formulas = list(formulas) or []
        force = kwargs.get("force", False)

        args = formulas + (["--force"] if force else [])
        cmd = "rm" if not self.cask else "zap"
        return self._spawn(cmd, args)

    def tap(self, tap):
        return self._spawn("tap", [tap] if tap is not None else [])

    def untap(self, tap):
        return self._spawn("untap", [tap])

    def ls(self):
        return self._spawn("ls", ["-1"], check_output=True).strip().split("\n")

    def uses(self, formula):
        args = ["--installed", "--recursive", formula]
        return self._spawn("uses", args, check_output=True).strip().split("\n")


class Defaults(object):
    def __init__(self, debug=None):
        self.debug = debug if debug is not None else False

    def write(self, domain, key, value, force=None):
        force = force if force is not None else False

        key_types = {
            bool: "-bool",
            float: "-float",
            int: "-int"
        }

        key_type = next(
            (k for t, k in key_types.items() if isinstance(value, t)),
            "-string"
        )

        args = ["defaults", "write"] + (["-f"] if force else [])
        args += [domain, key, key_type, str(value)]
        return spawn(args, debug=self.debug)

    def delete(self, domain, key):
        return spawn(["defaults", "delete", domain, key], debug=self.debug)


def spawn(args, **kwargs):
    check_call = kwargs.get("check_call", True)
    check_output = kwargs.get("check_output", False)
    debug = kwargs.get("debug", False)

    custom_params = ["check_call", "check_output", "debug"]
    params = dict((k, v) for (k, v) in kwargs.items()
                  if k not in custom_params)

    tty.putdebug(" ".join(args), debug)

    if check_output:
        return subprocess.check_output(args, **params)
    elif check_call:
        return subprocess.check_call(args, **params)
    else:
        return subprocess.call(args, **params)
