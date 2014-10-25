# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals
from uuid import uuid4
import os
import random


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


def random_case(string):
    return "".join(random.choice([c.upper(), c.lower()]) for c in string)


def random_str(fixed_length=None, min_length=None, max_length=None):
    min_length = min_length if min_length is not None else 0
    max_length = max_length if max_length is not None else 32
    if fixed_length is None:
        fixed_length = random.randint(min_length, max_length)
    return str(uuid4()).replace("-", "")[0:fixed_length]


def touch(fname):
    with open(fname, "a"):
        os.utime(fname, None)
