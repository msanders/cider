# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from cider import Cider
from cider.exceptions import BootstrapMissingError
from pytest import list_of, dict_of
import errno
import pytest
import random

try:
    from mock import MagicMock, patch
except ImportError:
    from unittest.mock import MagicMock, patch  # pylint: disable=F0401,E0611


@pytest.mark.randomize(cask=bool, debug=bool, verbose=bool)
class TestBrewCore(object):
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

    @pytest.mark.randomize(data=dict_of(str, str))
    def test_read_bootstrap(self, tmpdir, cask, debug, verbose, data):
        with patch("cider.core.read_json") as mock:
            cider = Cider(cask, debug, verbose, cider_dir=str(tmpdir))
            mock.return_value = data
            assert cider.read_bootstrap() == data
            mock.assert_called_with(cider.bootstrap_file)

            mock.side_effect = IOError(errno.ENOENT, "")
            with pytest.raises(BootstrapMissingError):
                cider.read_bootstrap()
                mock.assert_called_with(cider.bootstrap_file)

    @pytest.mark.randomize(random_prefix=str, bootstrap={
        "formulas": list_of(str),
        "casks": list_of(str)
    }, min_length=1)
    def test_installed(self, tmpdir, cask, debug, verbose,
                       random_prefix, bootstrap):
        cider = Cider(cask, debug, verbose, cider_dir=str(tmpdir))
        cider.read_bootstrap = MagicMock(return_value=bootstrap)

        key = "casks" if cask else "formulas"
        installed = bootstrap.get(key, [])
        random_choice = random.choice(installed) if installed else None
        for prefix in [None, random_choice, random_prefix]:
            assert cider.installed(prefix) == [
                x for x in installed if not prefix or x.startswith(prefix)
            ]

    @pytest.mark.randomize(
        installed=list_of(str),
        brewed=list_of(str),
        min_length=1
    )
    def test_missing(self, tmpdir, cask, debug, verbose,
                     installed, brewed):
        orphans = []

        def generate_uses():
            uses = {}
            for formula in brewed:
                subset = [x for x in installed if x != formula]
                if subset and random.choice([True, False]):
                    uses[formula] = random.sample(subset, random.randint(
                        1, len(subset)
                    ))
                else:
                    orphans.append(formula)

            return lambda x: uses.get(x, [])

        cider = Cider(cask, debug, verbose, cider_dir=str(tmpdir))
        cider.brew = MagicMock()
        cider.brew.ls = MagicMock(return_value=brewed)
        cider.brew.uses = MagicMock(side_effect=generate_uses())
        cider.installed = MagicMock(return_value=installed)

        assert cider.missing() == sorted(orphans)


@pytest.mark.randomize(debug=bool, verbose=bool)
class TestCiderCore(object):
    @pytest.mark.parametrize("bool_values", [
        "yes", "no", "y", "n", "true", "false"
    ])
    @pytest.mark.randomize(
        domain=str, key=str, values=[str, int, float], force=bool
    )
    def test_set_default(
        self, tmpdir, debug, verbose, domain, key, values, bool_values, force
    ):
        cider = Cider(False, debug, verbose, cider_dir=str(tmpdir))
        cider.defaults = MagicMock()

        for value in values + map(random_case, bool_values):
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

    @pytest.mark.randomize(data=dict_of(str, str))
    def test_read_defaults(self, tmpdir, debug, verbose, data):
        with patch("cider.core.read_json") as mock:
            cider = Cider(False, debug, verbose, cider_dir=str(tmpdir))
            mock.return_value = data

            assert cider.read_defaults() == data
            mock.assert_called_with(cider.defaults_file, {})
