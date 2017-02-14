"""
puni decorators
"""


from functools import wraps


def update_cache(func):
    """
    Decorates functions that modify the internally stored usernotes JSON so that
    updates are mirrored onto reddit

    Arguments:
        func: the function being decorated
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """
        The wrapper function
        """
        self.get_json()

        ret = func(self, *args, **kwargs)

        # If returning a string assume it is an update message
        if isinstance(ret, str):
            self.set_json(ret)
        else:
            return ret

    return wrapper
