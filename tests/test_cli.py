# -*- coding: utf-8 -*-
# pylint: disable=no-self-use
from __future__ import absolute_import, print_function, unicode_literals
from cider import _cli as cli
from click.testing import CliRunner
from pytest import nonempty_list_of
import pytest

try:
    from mock import patch
except ImportError:
    from unittest.mock import patch  # pylint: disable=F0401,E0611


@pytest.mark.randomize(cask=bool, debug=bool, verbose=bool)
class TestBrewCLI(object):
    @pytest.mark.randomize(formulas=nonempty_list_of(str), force=bool,
                           min_length=1)
    def test_install(self, cask, debug, verbose, formulas, force):
        cmd = self.__cask("install", cask)
        _test_command(
            cmd, formulas, debug=debug, verbose=verbose, force=force
        )

    @pytest.mark.randomize(formulas=nonempty_list_of(str), min_length=1)
    def test_rm(self, cask, debug, verbose, formulas):
        cmd = self.__cask("rm", cask)
        _test_command(
            cmd, formulas, debug=debug, verbose=verbose
        )

    @pytest.mark.randomize(formula=str, use_formula=bool)
    def test_list(self, cask, debug, verbose, formula, use_formula):
        cmd = self.__cask("ls", cask)
        args = [formula if use_formula else None]
        _test_command(
            cmd, args, debug=debug, verbose=verbose
        )

    def test_missing(self, cask, debug, verbose):
        cmd = self.__cask("missing", cask)
        _test_command(
            (cmd, "list_missing"), debug=debug, verbose=verbose
        )

    @staticmethod
    def __cask(cmd, cask):
        return "cask {0}".format(cmd) if cask else cmd


@pytest.mark.randomize(debug=bool, verbose=bool)
class TestCiderCLI(object):
    @pytest.mark.randomize(tap=str)
    def test_tap(self, debug, verbose, tap):
        _test_command("tap", [tap], debug=debug, verbose=verbose)

    def test_tap_missing(self, debug, verbose):
        _test_command(("tap missing", "list_missing_taps"),
                      debug=debug, verbose=verbose)

    @pytest.mark.randomize(
        name=str, key=str, value=str, globaldomain=bool, force=bool
    )
    def test_set_default(
        self, debug, verbose, name, key, value, globaldomain, force
    ):
        cmd, callback = "set-default", "set_default"
        result, MockCider = _invoke_command(
            cmd,
            [name, key, value],
            debug=debug,
            verbose=verbose,
            force=force,
            globalDomain=globaldomain
        )

        assert not result.exception
        assert result.exit_code == 0
        MockCider.assert_called_with(False, debug, verbose)

        if globaldomain:
            name, key, value = self.__global_domain_params(name, key)
        getattr(MockCider(), callback).assert_called_with(
            name, key, value, force=force
        )

    @pytest.mark.randomize(name=str, key=str, globaldomain=bool)
    def test_remove_default(self, debug, verbose, name, key, globaldomain):
        cmd, callback = "remove-default", "remove_default"
        result, MockCider = _invoke_command(
            cmd,
            [name, key],
            debug=debug,
            verbose=verbose,
            globalDomain=globaldomain
        )

        assert not result.exception
        assert result.exit_code == 0
        MockCider.assert_called_with(False, debug, verbose)

        if globaldomain:
            name, key, _ = self.__global_domain_params(name, key)
        getattr(MockCider(), callback).assert_called_with(name, key)

    def test_apply_defaults(self, debug, verbose):
        _test_command(
            ("apply-defaults", "apply_defaults"), debug=debug, verbose=verbose
        )

    @pytest.mark.randomize(app=str, icon=str)
    def test_set_icon(self, debug, verbose, app, icon):
        _test_command(
            ("set-icon", "set_icon"), [app, icon], debug=debug, verbose=verbose
        )

    @pytest.mark.randomize(app=str)
    def test_remove_icon(self, debug, verbose, app):
        _test_command(
            ("remove-icon", "remove_icon"), [app], debug=debug, verbose=verbose
        )

    def test_apply_icons(self, debug, verbose):
        _test_command(
            ("apply-icons", "apply_icons"), debug=debug, verbose=verbose
        )

    def test_run_scripts(self, debug, verbose):
        _test_command(
            ("run-scripts", "run_scripts"),
            debug=debug, verbose=verbose,
            expected_flags={
                "before": True,
                "after": True
            }
        )

    def test_restore(self, debug, verbose):
        _test_command("restore",
                      debug=debug,
                      verbose=verbose,
                      expected_flags={
                          "ignore_errors": False
                      })

    @pytest.mark.randomize(force=bool)
    def test_relink(self, debug, verbose, force):
        _test_command("relink", debug=debug, verbose=verbose, force=force)

    @pytest.mark.randomize(name=str, sources=nonempty_list_of(str),
                           min_length=1)
    def test_addlink(self, debug, verbose, name, sources):
        _test_command("addlink", [name] + sources,
                      debug=debug, verbose=verbose)

    @pytest.mark.randomize(name=str, min_length=1)
    def test_unlink(self, debug, verbose, name):
        _test_command("unlink", [name], debug=debug, verbose=verbose)

    @staticmethod
    def __global_domain_params(name, key):
        return "NSGlobalDomain", name, key


def _invoke_command(cmd, args, **flags):
    # TODO: Fix this
    start_flags = {
        "debug": flags.pop("debug", False),
        "verbose": flags.pop("verbose", False)
    }
    end_flags = _format_flags(flags)

    with patch("cider._cli.Cider") as MockCider:
        MockCider().debug = start_flags.get("debug")
        MockCider().verbose = start_flags.get("verbose")
        cliargs = [arg for arg in args if arg is not None] + end_flags
        result = CliRunner().invoke(
            cli.cli, _format_flags(start_flags) + cmd.split(" ") + cliargs
        )
        return (result, MockCider)


def _test_command(cmd, args=None, **flags):
    cmd, func = cmd if isinstance(cmd, tuple) else (cmd, cmd.split(" ")[-1])
    args = [] if args is None else args
    cask = cmd.split(" ")[0] == "cask"
    expected = flags.pop("expected_flags", {})
    result, MockCider = _invoke_command(cmd, args, **flags)

    debug = flags.pop("debug", False)
    verbose = flags.pop("verbose", False)
    flags.update(expected)

    assert not result.exception
    assert result.exit_code == 0
    MockCider.assert_called_with(cask, debug, verbose)
    getattr(MockCider(), func).assert_called_with(*args, **flags)


def _format_flags(flags):
    return ["--{0}".format(k) for k, v in flags.items() if v]
