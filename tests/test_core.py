# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from ._lib import assert_called_with_threshold
from cider import Cider
from pytest import list_of
import pytest

try:
    from mock import MagicMock
except ImportError:
    from unittest.mock import MagicMock  # pylint: disable=F0401,E0611


@pytest.mark.randomize(cask=bool)
class TestCider(object):
    @pytest.mark.randomize(formulas=list_of(str), force=bool)
    def test_install(self, tmpdir, cask, formulas, force):
        cider = Cider(cask, cider_dir=str(tmpdir))
        cider.brew = MagicMock()

        cider.install(*formulas, force=force)
        cider.brew.install.assert_called_once_with(*formulas, force=force)
        key = "casks" if cask else "formulas"
        for formula in formulas:
            assert formula in cider.read_bootstrap().get(key, [])

    @pytest.mark.randomize(formulas=list_of(str))
    def test_rm(self, tmpdir, cask, formulas):
        cider = Cider(cask, cider_dir=str(tmpdir))
        cider.brew = MagicMock()

        cider.rm(*formulas)
        cider.brew.rm.assert_called_once_with(*formulas)
        key = "casks" if cask else "formulas"
        for formula in formulas:
            assert formula not in cider.read_bootstrap().get(key, [])

    @pytest.mark.randomize(
        domain=str, key=str, values=[str, int, float], force=bool
    )
    def test_set_default(
        self, tmpdir, cask, domain, key, values, force
    ):
        def expected(value):
            return {
                "true": True,
                "false": False
            }.get(value, value)

        cider = Cider(cask, cider_dir=str(tmpdir))
        cider.defaults = MagicMock()

        for value in values:
            cider.set_default(domain, key, value, force=force)
            cider.defaults.write.assert_called_with(
                domain, key, expected(value), force
            )

            assert cider.read_defaults()[domain][key] == value

            # Verify str(value) => defaults.write(value)
            cider.set_default(domain, key, str(value), force=force)
            assert_called_with_threshold(
                cider.defaults.write,
                0.01,
                domain,
                key,
                value,
                force
            )

    @pytest.mark.randomize(domain=str, key=str)
    def test_remove_default(self, tmpdir, cask, domain, key):
        cider = Cider(cask, cider_dir=str(tmpdir))
        cider.defaults = MagicMock()
        cider.remove_default(domain, key)
        cider.defaults.delete.assert_called_with(domain, key)
        assert key not in cider.read_defaults().get(domain, [])

    @pytest.mark.randomize(tap=str)
    def test_tap(self, tmpdir, cask, tap):
        cider = Cider(cask, cider_dir=str(tmpdir))
        cider.brew = MagicMock()
        cider.tap(tap)
        cider.brew.tap.assert_called_with(tap)
        assert tap in cider.read_bootstrap().get("taps", [])

    @pytest.mark.randomize(tap=str)
    def test_untap(self, tmpdir, cask, tap):
        cider = Cider(cask, cider_dir=str(tmpdir))
        cider.brew = MagicMock()
        cider.untap(tap)
        cider.brew.untap.assert_called_with(tap)
        assert tap not in cider.read_bootstrap().get("taps", [])
