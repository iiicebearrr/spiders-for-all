import logging
import time
from functools import wraps
from typing import Callable

from rich.console import Console

from spiders_for_all.conf import settings
from spiders_for_all.core.exception import MaxRetryExceedError
from spiders_for_all.utils.logger import default_logger as logger


def retry(
    max_retries: int,
    interval: int,
    step: int,
    logger: logging.Logger | Console = logger,
):
    def negative(value: int):
        return value < 0

    if any(map(negative, (max_retries, interval, step))):
        raise ValueError("Value `max_retries`, `interval` and `step` should >= 0")

    def wrapper(func: Callable):
        @wraps(func)
        def inner(*args, **kwargs):
            pause_time = interval
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    if attempt == max_retries:
                        raise MaxRetryExceedError(max_retries)
                    msg = f"<Retry> [{attempt + 1}/{max_retries}]: {func.__name__} failed, sleep {pause_time}s for next try: {e.args}"
                    if isinstance(logger, logging.Logger):
                        logger.warn(msg, exc_info=settings.DEBUG)
                    else:
                        logger.log(msg)
                    time.sleep(pause_time)
                    pause_time += step

        return inner

    return wrapper
