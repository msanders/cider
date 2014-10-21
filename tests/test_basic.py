from cider import Cider
from mock import MagicMock, call
import pytest
import random


@pytest.mark.randomize(formulas=[str], cask=bool, force=bool)
def test_install(tmpdir, formulas, cask, force):
    cider = Cider(cider_dir=str(tmpdir), cask=cask)
    cider.brew = MagicMock()

    cider.install(*formulas, force=force)
    cider.brew.install.assert_called_once_with(*formulas, force=force)
    key = "casks" if cask else "formulas"
    for formula in formulas:
        assert formula in cider.read_bootstrap().get(key, [])


@pytest.mark.randomize(formulas=[str], cask=bool)
def test_rm(tmpdir, formulas, cask):
    cider = Cider(cider_dir=str(tmpdir), cask=cask)
    cider.brew = MagicMock()

    cider.rm(*formulas)
    cider.brew.rm.assert_called_once_with(*formulas)
    key = "casks" if cask else "formulas"
    for formula in formulas:
        assert formula not in cider.read_bootstrap().get(key, [])


@pytest.mark.randomize(
    domain=str, key=str, values=[str, int, float], force=bool
)
def test_set_default(tmpdir, domain, key, values, force):
    def expected(value):
        return {
            "true": True,
            "false": False
        }.get(value, value)

    cider = Cider(cider_dir=str(tmpdir))
    cider.defaults = MagicMock()

    for value in values:
        cider.set_default(domain, key, value, force=force)
        cider.defaults.write.assert_called_with(
            domain, key, expected(value), force
        )

        assert cider.read_defaults()[domain][key] == value

        # Verify str(value) => defaults.write(value)
        cider.set_default(domain, key, str(value), force=force)
        _assert_roughly_called_with(
            cider.defaults.write, domain, key, value, force
        )


@pytest.mark.randomize(domain=str, key=str)
def test_remove_default(tmpdir, domain, key):
    cider = Cider(cider_dir=str(tmpdir))
    cider.defaults = MagicMock()
    cider.remove_default(domain, key)
    cider.defaults.delete.assert_called_with(domain, key)
    assert key not in cider.read_defaults().get(domain, [])


@pytest.mark.randomize(tap=str)
def test_tap(tmpdir, tap):
    cider = Cider(cider_dir=str(tmpdir))
    cider.brew = MagicMock()
    cider.tap(tap)
    cider.brew.tap.assert_called_with(tap)
    assert tap in cider.read_bootstrap().get("taps", [])


@pytest.mark.randomize(tap=str)
def test_untap(tmpdir, tap):
    cider = Cider(cider_dir=str(tmpdir))
    cider.brew = MagicMock()
    cider.untap(tap)
    cider.brew.untap.assert_called_with(tap)
    assert tap not in cider.read_bootstrap().get("taps", [])


def _assert_roughly_called_with(mock_self, *args, **kwargs):
    def assert_roughly_equal(actual, expected):
        if isinstance(actual, float) and isinstance(expected, float):
            assert abs(actual - expected) <= threshold
        else:
            assert actual == expected

    threshold = 0.01
    _, actual_args, actual_kwargs = mock_self.mock_calls[-1]

    for actual, expected in zip(actual_args, args):
        assert_roughly_equal(actual, expected)

    for key, expected in kwargs.iteritems():
        assert_roughly_equal(actual_kwargs.get(key), expected)
