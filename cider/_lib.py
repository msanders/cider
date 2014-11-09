def lazyproperty(fn):
    @property
    def _lazyproperty(self):
        attr = "_" + fn.__name__
        if not hasattr(self, attr):
            setattr(self, attr, fn(self))
        return getattr(self, attr)

    return _lazyproperty
