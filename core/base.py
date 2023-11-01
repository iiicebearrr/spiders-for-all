from __future__ import annotations
import abc
import typing
from sqlalchemy import orm
from pydantic import BaseModel

SPIDERS: dict[str, typing.Type[Spider]] = {}


class Spider(abc.ABC):
    api: str
    name: str
    alias: str

    database_model: typing.Type[orm.DeclarativeBase]
    item_model: typing.Type[BaseModel]
    response_model: typing.Type[BaseModel] | None = None

    def __init__(self, *args, **kwargs):
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

    @abc.abstractmethod
    def run(self):
        pass
