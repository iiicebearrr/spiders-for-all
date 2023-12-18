from __future__ import annotations

import logging
import random
import time
import typing as t
from enum import Enum, auto
from itertools import batched

import requests
import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy import orm
from sqlalchemy.dialects import sqlite

from spiders_for_all.conf import settings
from spiders_for_all.database.session import SessionManager
from spiders_for_all.utils.decorator import retry
from spiders_for_all.utils.helper import not_none_else, user_agent_headers
from spiders_for_all.utils.logger import default_logger

SPIDERS: dict[str, dict[str, t.Type[BaseSpider]]] = {}


SleepInterval: t.TypeAlias = float | int | tuple[int, int]


class DbActionOnInit(Enum):
    CREATE_IF_NOT_EXIST = auto()
    DROP_AND_CREATE = auto()


class DbActionOnSave(Enum):
    DELETE_AND_CREATE = auto()
    UPDATE_OR_CREATE = auto()


class SpiderKwargs(t.TypedDict):
    logger: t.NotRequired[logging.Logger | None]
    db_action_on_init: t.NotRequired[DbActionOnInit | None]
    db_action_on_save: t.NotRequired[DbActionOnSave | None]
    max_retries: t.NotRequired[int]
    retry_interval: t.NotRequired[int]
    retry_step: t.NotRequired[int]


class Spider(t.Protocol):
    name: str
    alias: str

    def run(self):
        pass


class BaseSpider:
    api: str
    name: str
    alias: str
    platform: str

    database_model: t.Type[orm.DeclarativeBase]
    item_model: t.Type[BaseModel]
    response_model: t.Type[BaseModel] | None = None

    logger: logging.Logger = default_logger
    session_manager: SessionManager

    insert_batch_size: int = 100

    db_action_on_init: DbActionOnInit = DbActionOnInit.CREATE_IF_NOT_EXIST
    db_action_on_save: DbActionOnSave = DbActionOnSave.DELETE_AND_CREATE

    def __init__(
        self,
        *args,
        logger: logging.Logger | None = None,
        db_action_on_init: DbActionOnInit | None = None,
        db_action_on_save: DbActionOnSave | None = None,
        max_retries: int = settings.REQUEST_MAX_RETRIES,
        retry_interval: int = settings.REQUEST_RETRY_INTERVAL,
        retry_step: int = settings.REQUEST_RETRY_STEP,
        **kwargs,
    ):
        self.logger = logger or self.__class__.logger
        self.db_action_on_init = not_none_else(
            db_action_on_init, self.db_action_on_init
        )
        self.db_action_on_save = not_none_else(
            db_action_on_save, self.db_action_on_save
        )
        self.max_retries = int(max_retries)
        self.retry_interval = int(retry_interval)
        self.retry_step = int(retry_step)
        self.session = self.session_manager.session

        self.check_implementation()
        self.check_db()

    def check_implementation(self):
        attrs_required = [
            "api",
            "name",
            "alias",
            "platform",
            "database_model",
            "item_model",
            "session_manager",
        ]

        for attr in attrs_required:
            if getattr(self, attr, None) is None:
                raise ValueError(f"Attribute {attr} is required")

    def check_db(self):
        if self.db_action_on_init is DbActionOnInit.CREATE_IF_NOT_EXIST:
            self.session_manager.create_all([self.database_model])
        elif self.db_action_on_init is DbActionOnInit.DROP_AND_CREATE:
            self.session_manager.drop_all([self.database_model])
            self.session_manager.create_all([self.database_model], check=False)
        else:
            pass

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "name") and hasattr(cls, "alias") and hasattr(cls, "platform"):
            if cls.platform not in SPIDERS:
                SPIDERS[cls.platform] = {}

            spiders = SPIDERS[cls.platform]

            if cls.name in spiders:
                raise ValueError(
                    f"Duplicate spider name: {cls.name} for platform: {cls.platform}"
                )
            spiders[cls.name] = cls

            if cls.alias in spiders:
                raise ValueError(
                    f"Duplicate spider alias: {cls.alias} for platform: {cls.platform}"
                )
            spiders[cls.alias] = cls

    def before(self):
        """
        Called before the spider starts
        """
        self.info(f"[{'Start':^10}]: {self.name}[{self.alias}]")

    def after(self):
        """
        Called after the spider finishes
        """
        self.info(f"[{'Finished':^10}]: {self.name}[{self.alias}]")

    def request(self, method: str = "GET") -> requests.Response:
        @retry(
            max_retries=self.max_retries,
            interval=self.retry_interval,
            step=self.retry_step,
        )
        def _request():
            return self.send_request(method)

        return _request()

    def send_request(self, method: str = "GET") -> requests.Response:
        req_kwargs = self.get_request_args()

        self.debug(f"==> {method.upper()} {self.api}: {req_kwargs}")
        resp = requests.request(method, self.api, **req_kwargs)
        self.debug(f"<== {method.upper()} {resp.request.url}: {resp.status_code}")
        resp.raise_for_status()

        return resp

    def validate_response(
        self, response: requests.Response
    ) -> BaseModel | requests.Response:
        if self.response_model is not None:
            json_data = response.json()

            self.debug(f"<== Response json: {json_data}")
            return self.response_model(**json_data)
        return response

    def get_items_from_response(
        self, response: requests.Response | BaseModel
    ) -> t.Iterable[BaseModel]:
        raise NotImplementedError()

    def get_items(self) -> t.Iterable[BaseModel]:
        yield from self.get_items_from_response(self.validate_response(self.request()))

    def save_items(self, items: t.Iterable[BaseModel]):
        if self.db_action_on_save == DbActionOnSave.DELETE_AND_CREATE:
            self.delete_and_create_items(items)
        elif self.db_action_on_save == DbActionOnSave.UPDATE_OR_CREATE:
            self.update_or_create_items(items)
        else:
            raise ValueError(f"Invalid db action on save: {self.db_action_on_save}")

    def delete_and_create_items(self, items: t.Iterable[BaseModel]):
        """Delete and create items"""
        with self.session() as s:
            s.execute(sa.delete(self.database_model))
            for batched_items in batched(items, self.insert_batch_size):
                s.add_all(map(self.create_db_item, batched_items))
            s.commit()

    def create_db_item(self, item: BaseModel) -> orm.DeclarativeBase:
        return self.database_model(**self.item_to_dict(item))

    def item_to_dict(self, item: BaseModel, **extra) -> dict:
        return {**item.model_dump(), **extra}

    def update_or_create_items(self, items: t.Iterable[BaseModel]):
        """Update or create items"""
        insert_stmt = sqlite.insert(self.database_model).values(
            [self.item_to_dict(item) for item in items]
        )

        on_duplicate_key_stmt = insert_stmt.on_conflict_do_update(
            set_={
                field: getattr(insert_stmt.excluded, field)
                for field in self.item_model.model_fields
            }
        )

        with self.session() as s:
            s.execute(on_duplicate_key_stmt)
            s.commit()

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

    def get_request_args(self) -> dict:
        return {
            "headers": user_agent_headers(),
        }

    @classmethod
    def string(cls) -> str:
        return f"<Spider {cls.platform} {cls.name}({cls.alias})>"

    def run(self):
        self.before()
        self.save_items(self.get_items())
        self.after()


class PageSpider(BaseSpider):
    page_size: int = 20
    page_field: str = "page"
    page_size_field: str = "page_size"

    def __init__(
        self,
        total: int | None = None,
        page_size: int | None = None,
        start_page_number: int = 1,
        sleep_before_next_request: SleepInterval | None = None,
        **kwargs: t.Unpack[SpiderKwargs],
    ):
        super().__init__(**kwargs)

        self.page_size = int(not_none_else(page_size, self.page_size))
        self.page_number = int(start_page_number)
        self.sleep_before_next_request = sleep_before_next_request
        self.total = int(total) if total is not None else None
        self.end_page_number: int | None = (
            self.calculate_end_page(
                total=self.total,
                page_size=self.page_size,
                start_page_number=self.page_number,
            )
            if self.total is not None
            else None
        )

    def get_items(self) -> t.Iterable[BaseModel]:
        return_items_length = self.page_size

        while return_items_length == self.page_size:
            items = list(
                self.get_items_from_response(self.validate_response(self.request()))
            )
            yield from items

            # Stop if total specified
            if (
                self.end_page_number is not None
                and self.page_number == self.end_page_number
            ):
                break

            return_items_length = len(items)
            self.page_number += 1

            if (
                self.sleep_before_next_request is not None
                and return_items_length == self.page_size
            ):
                self.sleep()

    @classmethod
    def calculate_end_page(
        cls, total: int, page_size: int, start_page_number: int
    ) -> int:
        """
        Calculate the end page number

        :param total: Total number of items to be crawled
        :param page_size: Number of items per page
        :param start_page_number: Start page number
        :return: End page number
        """
        return (
            start_page_number
            + (total // page_size)
            + (1 if total % page_size else 0)
            - 1
        )

    def sleep(self):
        match self.sleep_before_next_request:
            case int():
                time.sleep(float(self.sleep_before_next_request))
            case float():
                time.sleep(self.sleep_before_next_request)
            case tuple():
                start, end = self.sleep_before_next_request
                time.sleep(random.randrange(start=start, stop=end))
            case _:
                raise TypeError(f"Invalid type: {type(self.sleep_before_next_request)}")

    def get_request_args(self) -> dict:
        return {
            **super().get_request_args(),
            "params": {
                self.page_field: self.page_number,
                self.page_size_field: self.page_size,
            },
        }


class SearchSpider(BaseSpider):
    def __init__(self, **kwargs: t.Unpack[SpiderKwargs]):
        # TODO: TypeDict for kwargs
        self.kwargs = kwargs
        super().__init__(**kwargs)


def run_spider(spider: t.Type[Spider], *args, **kwargs):
    spider(*args, **kwargs).run()
