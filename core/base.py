from __future__ import annotations

import abc
import logging
import typing
from collections import namedtuple

from pydantic import BaseModel
from sqlalchemy import orm

from conf import settings
from utils.logger import default_logger

SPIDERS: dict[str, typing.Type[Spider]] = {}

SpiderItem = namedtuple("SpiderItem", ["name", "alias", "spider"])


def get_all_spiders() -> dict[typing.Type[Spider], SpiderItem]:
    return {
        spider: SpiderItem(name=spider.name, alias=spider.alias, spider=spider)
        for spider in set(SPIDERS.values())
    }


class Spider(abc.ABC):
    api: str
    name: str
    alias: str

    database_model: typing.Type[orm.DeclarativeBase]
    item_model: typing.Type[BaseModel]
    response_model: typing.Type[BaseModel] | None = None

    logger: logging.Logger = default_logger

    def __init__(self, *args, **kwargs):
        self.logger = kwargs.get("logger", self.__class__.logger)
        if not all([self.database_model, self.item_model, self.response_model]):
            # ? Maybe let these three params be optional
            raise ValueError(
                "db_model, pydantic_model, response_model must be set before init"
            )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "name"):
            if cls.name in SPIDERS:
                raise ValueError(f"Duplicate spider name: {cls.name}")
            SPIDERS[cls.name] = cls
        if hasattr(cls, "alias"):
            if cls.alias in SPIDERS:
                raise ValueError(f"Duplicate spider alias: {cls.alias}")
            SPIDERS[cls.alias] = cls

    def log(self, msg: str, level: int = settings.LOG_LEVEL):
        self.logger.log(level, msg)

    def debug(self, msg: str):
        self.logger.debug(msg)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg, exc_info=True)

    def critical(self, msg: str):
        self.logger.critical(msg)

    @abc.abstractmethod
    def run(self):
        pass

    @classmethod
    def string(cls) -> str:
        return f"<Spider {cls.name}({cls.alias}). Database model: {cls.database_model}>"
