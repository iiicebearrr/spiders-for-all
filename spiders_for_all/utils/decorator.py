import time
from functools import wraps
from typing import Callable

from spiders_for_all.core.exception import MaxRetryExceedError
from spiders_for_all.utils.logger import default_logger as logger


def retry(max_retries: int, interval: int, step: int):
    def negative(value: int):
        return value < 0

    if any(map(negative, (max_retries, interval, step))):
        raise ValueError("Value `max_retries`, `interval` and `step` should >= 0")

    count = 0
    pause_time = interval

    def wrapper(func: Callable):
        @wraps(func)
        def inner(*args, **kwargs):
            nonlocal count
            nonlocal pause_time
            try:
                return func(*args, **kwargs)
            except KeyboardInterrupt:
                raise
            except Exception:
                if count == max_retries:
                    raise MaxRetryExceedError(max_retries)
                count += 1
                logger.debug(
                    f"<Retry> [{count}/{max_retries}]: {func.__name__} failed, sleep {pause_time}s for next try"
                )
                time.sleep(pause_time)
                pause_time += step
                return inner(*args, **kwargs)

        return inner

    return wrapper
