# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from ._lib import random_case, random_str, touch
from cider import Cider
from cider.exceptions import BootstrapMissingError, SymlinkError
from cider._sh import isdirname
from pytest import list_of, dict_of
from glob import iglob
import errno
import os
import pytest
import random

try:
    from contextlib import nested as empty
    from mock import MagicMock, patch
except ImportError:
    from contextlib import ExitStack as empty  # noqa pylint: disable=E0611
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

    @pytest.mark.randomize(force=bool)
    def test_relink(self, tmpdir, debug, verbose, force):
        """
        Tests that:
        1. Target directories are created.
        2. For each source in glob(key), mklink(src, expandtarget(src, target))
           is called.
        3. Previously-cached targets are removed.
        4. Cache is updated with new targets.
        """
        def generate_symlinks():
            srcdir = tmpdir.join(random_str(min_length=1))

            def symkey(directory, key):
                return str(directory.join(key).relto(srcdir))

            def symvalue(directory, value):
                return str(directory.join(value)) + (
                    "/" if value.endswith("/") else ""
                )

            outerdir = srcdir.join(random_str(min_length=1))
            innerdir = outerdir.join(random_str(min_length=1))
            targetdir = tmpdir.join(random_str(min_length=1))

            ext = random_str(min_length=1, max_length=8)
            os.makedirs(str(innerdir))

            for _ in range(random.randint(0, 10)):
                touch(str(innerdir.join("{0}.{1}".format(random_str(), ext))))

            path = str(outerdir.join(random_str(min_length=1)))
            touch(path)

            return {
                symkey(outerdir, "*/*." + ext): symvalue(targetdir, "a/b/c/"),
                symkey(outerdir, "*/*." + ext): symvalue(targetdir, "a/b/c"),
                symkey(outerdir, path): symvalue(targetdir, "a/b/d"),
            }

        cider = Cider(False, debug, verbose, cider_dir=str(tmpdir))
        cider.mklink = MagicMock(return_value=True)

        for srcglob, target in generate_symlinks().items():
            invalid = not isdirname(target) and ("*" in srcglob or
                                                 "?" in srcglob)
            old_targets = cider._cached_targets()  # pylint:disable=W0212
            cider.read_bootstrap = MagicMock(return_value={
                "symlinks": {srcglob: target}
            })

            with pytest.raises(SymlinkError) if invalid else empty():
                new_targets = set(cider.relink(force))
                for src in iglob(srcglob):
                    cider.mklink.assert_called_with(src, cider.expandtarget(
                        src, target
                    ))

                assert os.path.isdir(os.path.dirname(target))
                for dead_target in set(old_targets) - new_targets:
                    assert not os.path.exists(dead_target)

                new_cache = cider._cached_targets()  # pylint:disable=W0212
                assert new_targets == set(new_cache).intersection(new_targets)

    def test_mklink(self, tmpdir, debug, verbose):
        cider = Cider(False, debug, verbose, cider_dir=str(tmpdir))
        source = str(tmpdir.join(random_str(min_length=1)))
        target = str(tmpdir.join(random_str(min_length=1)))

        # SymlinkError should be raised if source does not exist.
        with pytest.raises(SymlinkError):
            assert not cider.mklink(source, target)

        # Should succeed for valid source/target.
        touch(source)
        for _ in range(2):
            assert cider.mklink(source, target)
            assert os.path.islink(target)

        # Should fail for existing target.
        os.remove(target)
        touch(target)
        assert not cider.mklink(source, target)
        assert not os.path.islink(target)

        # Should allow removing existing target with --force.
        with patch("cider._osx.move_to_trash", side_effect=os.remove):
            assert cider.mklink(source, target, force=True)

    @pytest.mark.randomize(defaults=dict_of(str, dict_of(str, str)))
    def test_apply_defaults(self, tmpdir, debug, verbose, defaults):
        cider = Cider(False, debug, verbose, cider_dir=str(tmpdir))
        cider.defaults = MagicMock()
        cider.read_defaults = MagicMock(return_value=defaults)
        cider.apply_defaults()

        for domain, options in defaults.items():
            for key, value in options.items():
                cider.defaults.write.assert_any_call(domain, key, value)

    @pytest.mark.randomize(before=bool, after=bool, bootstrap={
        "before-scripts": list_of(str),
        "after-scripts": list_of(str)
    })
    def test_run_scripts(self, tmpdir, debug, verbose, before,
                         after, bootstrap):
        cider = Cider(False, debug, verbose, cider_dir=str(tmpdir))
        cider.read_bootstrap = MagicMock(return_value=bootstrap)
        scripts = []
        scripts += bootstrap.get("before-scripts", []) if before else []
        scripts += bootstrap.get("after-scripts", []) if after else []

        # TODO: Assert ordering
        with patch("cider.core.spawn", autospec=True, return_value=0) as spawn:
            cider.run_scripts(before, after)
            for script in scripts:
                spawn.assert_any_call(
                    [script], shell=True, debug=debug, cwd=cider.cider_dir
                )


def setup_module():
    random.seed()
