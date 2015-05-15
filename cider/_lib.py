from functools import wraps

def lazyproperty(fn):
    @property
    @wraps(fn)
    def _lazyproperty(self):
        attr = "_" + fn.__name__
        if not hasattr(self, attr):
            setattr(self, attr, fn(self))
        return getattr(self, attr)

    return _lazyproperty
