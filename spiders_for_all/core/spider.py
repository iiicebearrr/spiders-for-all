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
from spiders_for_all.core.client import HttpClient, RequestKwargs
from spiders_for_all.core.response import Response
from spiders_for_all.database.session import SessionManager
from spiders_for_all.utils.decorator import retry
from spiders_for_all.utils.helper import not_none_else
from spiders_for_all.utils.logger import LoggerMixin, default_logger

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


class BaseSpider(LoggerMixin):
    api: str
    name: str
    alias: str
    platform: str
    description: str = ""

    database_model: t.Type[orm.DeclarativeBase]
    item_model: t.Type[BaseModel]
    response_model: t.Type[Response] | None = None

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
        **kwargs,
    ):
        super().__init__(logger=logger or self.__class__.logger)
        self.db_action_on_init = not_none_else(
            db_action_on_init, self.db_action_on_init
        )
        self.db_action_on_save = not_none_else(
            db_action_on_save, self.db_action_on_save
        )
        self.session = self.session_manager.session

        self.check_implementation()
        self.check_db()

        self.client = HttpClient(logger=self.logger)
        self.response: Response | None = None

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
        if hasattr(cls, "name") and hasattr(cls, "alias") and hasattr(cls, "platform"):
            if cls.platform not in SPIDERS:
                SPIDERS[cls.platform] = {}

            spiders = SPIDERS[cls.platform]

            spiders[cls.name] = cls

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

    def validate_response(
        self, response: requests.Response
    ) -> BaseModel | requests.Response:
        if self.response_model is not None:
            json_data = response.json()

            # self.debug(f"<== Response json: {json_data}")

            ret = self.response_model(**json_data)
            ret.raise_for_status()
        else:
            ret = response

        self.response = ret  # type: ignore
        return ret

    def get_items_from_response(
        self, response: requests.Response | BaseModel
    ) -> t.Iterable[BaseModel]:
        raise NotImplementedError()

    def request_items(self, method: str, url: str, **kwargs: t.Unpack[RequestKwargs]):
        return self.client.request(method, url, **kwargs)

    def _get_items(self) -> t.Iterable[BaseModel]:
        # Note: get_items_from_response and validate_response should be retried either if failed
        @retry(
            max_retries=self.client.retry_settings.get(
                "max_retries", settings.REQUEST_MAX_RETRIES
            ),
            interval=self.client.retry_settings.get(
                "retry_interval", settings.REQUEST_RETRY_INTERVAL
            ),
            step=self.client.retry_settings.get(
                "retry_step", settings.REQUEST_RETRY_STEP
            ),
        )
        def wrapper():
            return self.get_items_from_response(
                self.validate_response(
                    self.request_items("GET", self.api, **self.get_request_args())
                )
            )

        return wrapper()  # type: ignore

    def get_items(self) -> t.Iterable[BaseModel]:
        with self.client:
            yield from self._get_items()  # type: ignore

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
                self.info(f"Insert {len(batched_items)} items...")

    def create_db_item(self, item: BaseModel) -> orm.DeclarativeBase:
        return self.database_model(**self.item_to_dict(item))

    def item_to_dict(self, item: BaseModel, **extra) -> dict:
        return {**item.model_dump(), **extra}

    def update_or_create_items(self, items: t.Iterable[BaseModel]):
        """Update or create items"""
        with self.session() as s:
            for batched_items in batched(items, self.insert_batch_size):
                insert_stmt = sqlite.insert(self.database_model).values(
                    [self.item_to_dict(item) for item in batched_items]
                )

                on_duplicate_key_stmt = insert_stmt.on_conflict_do_update(
                    set_={
                        field: getattr(insert_stmt.excluded, field)
                        for field in self.item_model.model_fields
                        if hasattr(insert_stmt.excluded, field)
                    }
                )

                s.execute(on_duplicate_key_stmt)
                s.commit()
                self.info(f"Create or update {len(batched_items)} items...")

    def get_request_args(self) -> dict:
        return {}

    @classmethod
    def string(cls) -> str:
        return f"<{cls.platform}> {cls.name}({cls.alias}){f": {cls.description}" if cls.description else ""}"

    def run(self):
        self.before()
        self.save_items(self.get_items())
        self.after()


class RateLimitMixin:
    def sleep(self, sleep_before_next_request: SleepInterval | None = None):
        match sleep_before_next_request:
            case int() | str():
                time.sleep(float(sleep_before_next_request))
            case float():
                time.sleep(sleep_before_next_request)

            case tuple():
                start, end = sleep_before_next_request
                time.sleep(random.randrange(start=start, stop=end))
            case _:
                pass


class PageSpider(BaseSpider, RateLimitMixin):
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
        with self.client:
            return_items_length = self.page_size

            count = 0

            while return_items_length == self.page_size:
                items = list(self._get_items())

                if self.total is None:
                    yield from items
                else:
                    for item in items:
                        yield item
                        count += 1
                        if count == self.total:
                            break

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
                    self.sleep(self.sleep_before_next_request)

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

    def get_request_args(self) -> dict:
        return {
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
