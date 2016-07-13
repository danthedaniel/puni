"""
puni decorators
"""


from functools import wraps


def update_cache(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.get_json()

        ret = func(self, *args, **kwargs)

        if isinstance(ret, str):
            self.set_json(ret)
        else:
            return ret

    return wrapper
