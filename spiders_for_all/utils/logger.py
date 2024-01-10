import logging
import logging.config
import typing as t
from traceback import format_exc

from rich import console

from spiders_for_all.conf import settings

LoggerType: t.TypeAlias = console.Console | logging.Logger

LEVEL = settings.LOG_LEVEL

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "rich": {
            "format": "%(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "file": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "level": LEVEL,
            "class": "rich.logging.RichHandler",
            "formatter": "rich",
        },
        "bilibili-file": {
            "level": LEVEL,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": settings.WORKDIR / "logs" / "bilibili.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "file",
        },
        "xhs-file": {
            "level": LEVEL,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": settings.WORKDIR / "logs" / "xhs.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "file",
        },
    },
    "loggers": {
        "bilibili": {
            "handlers": ["default", "bilibili-file"],
            "level": LEVEL,
            "propagate": True,
        },
        "xhs": {
            "handlers": ["default", "xhs-file"],
            "level": LEVEL,
            "propagate": True,
        },
        "default": {
            "handlers": ["default"],
            "level": LEVEL,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)


def get_logger(name: str):
    return logging.getLogger(name)


default_logger = get_logger("default")


class LoggerMixin:
    def __init__(self, logger: LoggerType = default_logger, **kwargs) -> None:
        self.logger = logger

    def console_log(self, msg: str, level: int = logging.INFO, **kwargs) -> None:
        _console: console.Console = self.logger  # type: ignore
        if level >= settings.LOG_LEVEL:
            msg = f"[{logging.getLevelName(level)}] {msg}"
            if "exc_info" in kwargs:
                msg += "\n" + format_exc()
            _console.log(msg)

    def log(self, msg: str, level: int = logging.INFO, **kwargs) -> None:
        if isinstance(self.logger, logging.Logger):
            self.logger.log(level, msg, **kwargs)
        elif isinstance(self.logger, console.Console):
            self.console_log(msg, level, **kwargs)
        else:
            raise TypeError(
                f"Logger type must be {logging.Logger} or {console.Console}, "
                f"but got {type(self.logger)}."
            )

    def debug(self, msg: str) -> None:
        self.log(msg, level=logging.DEBUG)

    def info(self, msg: str) -> None:
        self.log(msg, level=logging.INFO)

    def warning(self, msg: str) -> None:
        self.log(msg, level=logging.WARNING)

    def error(self, msg: str) -> None:
        self.log(msg, level=logging.ERROR, exc_info=True)

    def critical(self, msg: str) -> None:
        self.log(msg, level=logging.CRITICAL, exc_info=True)
