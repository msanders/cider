# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

notset = object()


# This class allows us to safely patch objects without foregoing the static
# analyzer complaints mock's monkeypatch causes (e.g. E1103).
class Patcher(object):
    def __init__(self, attrs=None):
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
