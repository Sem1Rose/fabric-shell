import time
from functools import wraps
from collections.abc import Callable


def cooldown(
    cooldown_time: float, error: Callable | None = None, return_error: bool = False
):
    def decorator(func):
        last_call_time = 0

        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal last_call_time
            current_time = time.monotonic()
            elapsed_time = current_time - last_call_time
            if elapsed_time >= cooldown_time:
                result = func(*args, **kwargs)
                last_call_time = current_time
                return result
            else:
                if return_error is True and error is not None:
                    return error((cooldown_time - elapsed_time), *args, **kwargs)
                elif error is not None:
                    error((cooldown_time - elapsed_time), *args, **kwargs)

        return wrapper

    return decorator
