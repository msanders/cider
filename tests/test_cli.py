# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from ._lib import Patcher
from cider import cli
from click.testing import CliRunner
from pytest import list_of
import pytest

try:
    from mock import MagicMock
except ImportError:
    from unittest.mock import MagicMock  # pylint: disable=F0401,E0611


@pytest.mark.randomize(debug=bool, verbose=bool)
class TestCLI(object):
    @pytest.mark.randomize(formula=list_of(str, min_items=1), force=bool)
    def test_install(self, debug, verbose, formula, force):
        self.__test_command(
            "install", formula, debug=debug, verbose=verbose, force=force
        )

    @pytest.mark.randomize(formula=list_of(str, min_items=1))
    def test_rm(self, debug, verbose, formula):
        self.__test_command(
            "rm", formula, debug=debug, verbose=verbose
        )

    @pytest.mark.randomize(formula=str, use_formula=bool)
    def test_list(self, debug, verbose, formula, use_formula):
        args = [formula if use_formula else None]
        self.__test_command(
            "ls", args, debug=debug, verbose=verbose
        )

    def test_missing(self, debug, verbose):
        self.__test_command(
            ("missing", "list_missing"), debug=debug, verbose=verbose
        )

    @pytest.mark.randomize(
        name=str, key=str, value=str, globaldomain=bool, force=bool
    )
    def test_set_default(
        self, debug, verbose, name, key, value, globaldomain, force
    ):
        cmd, callback = "set-default", "set_default"
        result, MockCider = self.__invoke_command(
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
        result, MockCider = self.__invoke_command(
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
        self.__test_command(
            ("apply-defaults", "apply_defaults"), debug=debug, verbose=verbose
        )

    @pytest.mark.randomize(app=str, icon=str)
    def test_set_icon(self, debug, verbose, app, icon):
        self.__test_command(
            ("set-icon", "set_icon"), [app, icon], debug=debug, verbose=verbose
        )

    @pytest.mark.randomize(app=str)
    def test_remove_icon(self, debug, verbose, app):
        self.__test_command(
            ("remove-icon", "remove_icon"), [app], debug=debug, verbose=verbose
        )

    def apply_icons(self, debug, verbose):
        self.__test_command(
            ("apply-icons", "apply_icons"), debug=debug, verbose=verbose
        )

    def run_scripts(self, debug, verbose):
        self.__test_command(
            ("run-scripts", "run_scripts"), debug=debug, verbose=verbose
        )

    def restore(self, debug, verbose):
        self.__test_command("restore", debug=debug, verbose=verbose)

    def relink(self, debug, verbose):
        self.__test_command("relink", debug=debug, verbose=verbose)

    def __invoke_command(self, cmd, args, **flags):
        # TODO: Fix this
        start_flags = self.__format_flags({
            "debug": flags.pop("debug", False),
            "verbose": flags.pop("verbose", False)
        })
        end_flags = self.__format_flags(flags)

        with Patcher((cli, "Cider")):
            MockCider = cli.Cider = MagicMock()
            cliargs = [arg for arg in args if arg is not None] + end_flags
            result = CliRunner().invoke(
                cli.cli, start_flags + cmd.split(" ") + cliargs
            )
            return (result, MockCider)

    def __test_command(self, cmd, args=None, **flags):
        cmd, callback = cmd if isinstance(cmd, tuple) else (cmd, cmd)
        args = [] if args is None else args
        result, MockCider = self.__invoke_command(cmd, args, **flags)
        debug = flags.pop("debug", False)
        verbose = flags.pop("verbose", False)

        assert not result.exception
        assert result.exit_code == 0
        MockCider.assert_called_with(False, debug, verbose)
        getattr(MockCider(), callback).assert_called_with(*args, **flags)

    @staticmethod
    def __format_flags(flags):
        return ["--{0}".format(k) for k, v in flags.items() if v]

    @staticmethod
    def __global_domain_params(name, key):
        return "NSGlobalDomain", name, key
