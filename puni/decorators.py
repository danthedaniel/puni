"""
puni decorators
"""


from functools import wraps


def update_cache(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.get_json()

        ret = func(self, *args, **kwargs)

        # If returning a string assume it is an update message
        if isinstance(ret, str):
            self.set_json(ret)
        else:
            return ret

    return wrapper
