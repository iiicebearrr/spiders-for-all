import logging
import logging.config

from conf import settings

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
        "file": {
            "level": LEVEL,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": settings.BASE_DIR / "bilibili" / "bilibili.log",
            "maxBytes": 1024 * 1024 * 10,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "file",
        },
    },
    "loggers": {
        "bilibili": {
            "handlers": ["default", "file"],
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
