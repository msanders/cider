# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from cider import Cider
from pytest import list_of
import pytest

try:
    from mock import MagicMock
except ImportError:
    from unittest.mock import MagicMock  # pylint: disable=F0401,E0611


@pytest.mark.randomize(cask=bool, debug=bool, verbose=bool)
class TestBrewCore(object):
    @pytest.mark.randomize(formulas=list_of(str, min_items=1), force=bool)
    @pytest.mark.randomize(
        formulas=list_of(str, min_items=1), force=bool, min_length=1
    )
    def test_install(self, tmpdir, cask, debug, verbose, formulas, force):
        cider = Cider(cask, debug, verbose, cider_dir=str(tmpdir))
        cider.brew = MagicMock()

        cider.install(*formulas, force=force)
        cider.brew.install.assert_called_once_with(*formulas, force=force)
        key = "casks" if cask else "formulas"
        for formula in formulas:
            assert formula in cider.read_bootstrap().get(key, [])

    @pytest.mark.randomize(formulas=list_of(str, min_items=1), min_length=1)
    def test_rm(self, tmpdir, cask, debug, verbose, formulas):
        cider = Cider(cask, debug, verbose, cider_dir=str(tmpdir))
        cider.brew = MagicMock()

        cider.rm(*formulas)
        cider.brew.rm.assert_called_once_with(*formulas)
        key = "casks" if cask else "formulas"
        for formula in formulas:
            assert formula not in cider.read_bootstrap().get(key, [])

    @pytest.mark.randomize(
        prefix=str, bootstrap={"formulas": list_of(str), "casks": list_of(str)}
    )
    def test_installed(self, tmpdir, cask, debug, verbose, prefix, bootstrap):
        cider = Cider(cask, debug, verbose, cider_dir=str(tmpdir))
        cider.brew = MagicMock()
        cider.read_bootstrap = MagicMock(return_value=bootstrap)

        key = "casks" if cask else "formulas"
        mock_installed = bootstrap[key]
        if prefix:
            mock_installed = [
                x for x in mock_installed if x.startswith(prefix)
            ]

        installed = cider.installed(prefix or None)
        assert mock_installed == installed


@pytest.mark.randomize(debug=bool, verbose=bool)
class TestCiderCore(object):
    @pytest.mark.randomize(
        domain=str, key=str, values=[str, int, float], force=bool
    )
    def test_set_default(
        self, tmpdir, debug, verbose, domain, key, values, force
    ):
        cider = Cider(False, debug, verbose, cider_dir=str(tmpdir))
        cider.defaults = MagicMock()

        for value in values + ["YES", "NO"]:
            json_value = cider.json_value(value)
            cider.set_default(domain, key, value, force=force)
            cider.defaults.write.assert_called_with(
                domain, key, json_value, force
            )

            assert cider.read_defaults()[domain][key] == json_value

            # Verify str(value) => defaults.write(value)
            cider.set_default(domain, key, str(value), force=force)
            cider.defaults.write.assert_called_with(
                domain, key, cider.json_value(str(value)), force
            )

    @pytest.mark.randomize(domain=str, key=str)
    def test_remove_default(self, tmpdir, debug, verbose, domain, key):
        cider = Cider(False, debug, verbose, cider_dir=str(tmpdir))
        cider.defaults = MagicMock()
        cider.remove_default(domain, key)
        cider.defaults.delete.assert_called_with(domain, key)
        assert key not in cider.read_defaults().get(domain, [])

    @pytest.mark.randomize(tap=str)
    def test_tap(self, tmpdir, debug, verbose, tap):
        cider = Cider(False, debug, verbose, cider_dir=str(tmpdir))
        cider.brew = MagicMock()
        cider.tap(tap)
        cider.brew.tap.assert_called_with(tap)
        assert tap in cider.read_bootstrap().get("taps", [])

    @pytest.mark.randomize(tap=str)
    def test_untap(self, tmpdir, debug, verbose, tap):
        cider = Cider(False, debug, verbose, cider_dir=str(tmpdir))
        cider.brew = MagicMock()
        cider.untap(tap)
        cider.brew.untap.assert_called_with(tap)
        assert tap not in cider.read_bootstrap().get("taps", [])
