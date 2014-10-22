# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from ._lib import Patcher
from cider import _sh as sh
from cider._sh import Brew, Defaults
from pytest import list_of
from subprocess import CalledProcessError
import pytest
import random
import subprocess

try:
    from contextlib import nested as empty
    from mock import MagicMock
except ImportError:
    from contextlib import ExitStack as empty
    from unittest.mock import MagicMock


@pytest.mark.randomize(cask=bool, debug=bool, verbose=bool)
class TestBrew(object):
    patcher = Patcher()

    @classmethod
    def setup_class(cls):
        cls.patcher.saveattrs((sh, "spawn"))
        sh.spawn = MagicMock(return_value=0)

    @classmethod
    def teardown_class(cls):
        cls.patcher.teardown()

    @pytest.mark.randomize(formulas=list_of(str), force=bool)
    def test_install(self, cask, debug, verbose, formulas, force):
        brew = Brew(cask, debug, verbose)
        args = self.__cmd(cask)
        args += ["install"] + formulas + (["--force"] if force else [])
        args += self.__flags(debug, verbose)

        brew.install(*formulas, force=force)
        sh.spawn.assert_called_with(args, debug=debug, check_output=False)

    @pytest.mark.randomize(formulas=list_of(str))
    def test_rm(self, cask, debug, verbose, formulas):
        brew = Brew(cask, debug, verbose)
        args = self.__cmd(cask) + ["zap" if cask else "rm"] + formulas
        args += self.__flags(debug, verbose)

        brew.rm(*formulas)
        sh.spawn.assert_called_with(args, debug=debug, check_output=False)

    @pytest.mark.randomize(formula=str)
    def test_safe_install(self, cask, debug, verbose, formula):
        brew = Brew(cask, debug, verbose)
        old_side_effect = sh.spawn.side_effect

        args = self.__cmd(cask) + ["install", formula]
        args += self.__flags(debug, verbose)
        sh.spawn.side_effect = CalledProcessError(42, " ".join(args))

        brew.safe_install(formula)
        sh.spawn.assert_called_with(args, debug=debug, check_output=False)
        sh.spawn.side_effect = old_side_effect

    @pytest.mark.randomize(tap=str, use_tap=bool)
    def test_tap(self, cask, debug, verbose, tap, use_tap):
        with pytest.raises(AssertionError) if cask else empty():
            brew = Brew(cask, debug, verbose)
            tap = tap if use_tap else None
            args = self.__cmd() + ["tap"] + ([tap] if tap is not None else [])
            args += self.__flags(debug, verbose)

            brew.tap(tap)
            sh.spawn.assert_called_with(args, debug=debug, check_output=False)

    @pytest.mark.randomize(tap=str)
    def test_untap(self, cask, debug, verbose, tap):
        with pytest.raises(AssertionError) if cask else empty():
            brew = Brew(cask, debug, verbose)
            args = self.__cmd() + ["untap", tap]
            args += self.__flags(debug, verbose)

            brew.untap(tap)
            sh.spawn.assert_called_with(args, debug=debug, check_output=False)

    @pytest.mark.randomize()
    def test_ls(self, cask, debug, verbose):
        brew = Brew(cask, debug, verbose)
        old_return, sh.spawn.return_value = sh.spawn.return_value, ""
        args = self.__cmd(cask) + ["ls", "-1"]

        brew.ls()
        sh.spawn.assert_called_with(args, debug=debug, check_output=True)
        sh.spawn.return_value = old_return

    @pytest.mark.randomize(formula=str)
    def test_uses(self, cask, debug, verbose, formula):
        brew = Brew(cask, debug, verbose)
        old_return, sh.spawn.return_value = sh.spawn.return_value, ""
        args = self.__cmd(cask)
        args += ["uses", "--installed", "--recursive", formula]
        args += self.__flags(debug, verbose)

        brew.uses(formula)
        sh.spawn.assert_called_with(args, debug=debug, check_output=True)
        sh.spawn.return_value = old_return

    def __cmd(self, cask=None):
        return ["brew"] + (["cask"] if cask else [])

    def __flags(self, debug, verbose):
        return ((["--debug"] if debug else []) +
                (["--verbose"] if verbose else []))


@pytest.mark.randomize(debug=bool)
class TestDefaults(object):
    patcher = Patcher()

    @classmethod
    def setup_class(cls):
        cls.patcher.saveattrs((sh, "spawn"))
        sh.spawn = MagicMock(return_value=0)

    @classmethod
    def teardown_class(cls):
        cls.patcher.teardown()

    @pytest.mark.randomize(domain=str, key=str, value=str, force=bool)
    def test_write(self, debug, domain, key, value, force):
        defaults = Defaults(debug)
        args = ["defaults", "write"] + (["-f"] if force else [])
        args += [domain, key, defaults.key_type(value), str(value)]

        defaults.write(domain, key, value, force)
        sh.spawn.assert_called_with(args, debug=debug)

    @pytest.mark.randomize(domain=str, key=str)
    def test_delete(self, debug, domain, key):
        defaults = Defaults(debug)
        args = ["defaults", "delete", domain, key]

        defaults.delete(domain, key)
        sh.spawn.assert_called_with(args, debug=debug)


@pytest.mark.randomize(
    args=list_of(str), check_call=bool, check_output=bool, debug=bool
)
def test_spawn(args, check_call, check_output, debug):
    patches = [
        (subprocess, "check_output"),
        (subprocess, "check_call"),
        (subprocess, "call")
    ]

    with Patcher(patches):
        if check_output:
            expected_mock = subprocess.check_output = MagicMock()
        elif check_call:
            expected_mock = subprocess.check_call = MagicMock()
        else:
            expected_mock = subprocess.call = MagicMock()

        expected_mock.return_value = random.randint(0, 100)
        actual_return_value = sh.spawn(
            args, check_call=check_call, check_output=check_output, debug=debug
        )

        expected_mock.assert_called_with(args)
        assert actual_return_value == expected_mock.return_value


def setup_module():
    random.seed()
    sh.click.confirm = MagicMock(return_value=True)
