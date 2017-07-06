"""Copyright 2017 teaearlgraycold.

This file is part of puni

puni is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

puni is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
details. You should have received a copy of the GNU General Public License along
with puni. If not, see http://www.gnu.org/licenses/.
"""


from functools import wraps


def update_cache(func):
    """Decorate functions that modify the internally stored usernotes JSON.

    Ensures that updates are mirrored onto reddit.

    Arguments:
        func: the function being decorated
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        """The wrapper function."""
        lazy = kwargs.get('lazy', False)
        kwargs.pop('lazy', None)

        if not lazy:
            self.get_json()

        ret = func(self, *args, **kwargs)

        # If returning a string assume it is an update message
        if isinstance(ret, str) and not lazy:
            self.set_json(ret)
        else:
            return ret

    return wrapper
