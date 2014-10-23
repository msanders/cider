# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

notset = object()


# This class allows us to safely patch objects without foregoing the static
# analyzer complaints mock's monkeypatch causes (e.g. E1103).
class Patcher(object):
    def __init__(self, *attrs):
        attrs = [] if attrs is None else attrs
        self.__patched_attrs = []
        self.saveattrs(*attrs)

    def __enter__(self):
        return self

    def __exit__(self, value_type, value, traceback):
        self.teardown()

    def saveattrs(self, *attrs):
        for obj, name in attrs:
            value = getattr(obj, name, notset)
            self.__patched_attrs.append((obj, name, value))

    def teardown(self):
        for obj, name, value in self.__patched_attrs:
            if value is notset:
                delattr(obj, name)
            else:
                setattr(obj, name, value)
        self.__patched_attrs = []


def threshold_comparator(threshold):
    def comparator(actual, expected):
        if isinstance(actual, float) and isinstance(expected, float):
            return abs(actual - expected) <= threshold
        else:
            return actual == expected

    return comparator


def assert_called_with_comparator(mock_self, comparator, *args, **kwargs):
    _, actual_args, actual_kwargs = mock_self.mock_calls[-1]

    for actual, expected in zip(actual_args, args):
        assert comparator(actual, expected)

    for key, expected in kwargs.items():
        assert comparator(actual_kwargs.get(key), expected)


def assert_called_with_threshold(mock_self, threshold, *args, **kwargs):
    assert_called_with_comparator(
        mock_self,
        threshold_comparator(threshold),
        *args,
        **kwargs
    )
