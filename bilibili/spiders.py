from __future__ import annotations

import abc
import typing
from functools import cached_property

import requests
import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy import orm

from bilibili import db
from bilibili import models
from utils import helper

Session = db.Session

SPIDERS: dict[str, typing.Type[Spider]] = {}


class Spider(abc.ABC):
    api: str
    name: str

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
            SPIDERS[cls.name] = cls

    @abc.abstractmethod
    def run(self):
        pass


def calculate_end_page(total: int, page_size: int, start_page_number: int) -> int:
    """
    Calculate the end page number

    :param total: Total number of items to be crawled
    :param page_size: Number of items per page
    :param start_page_number: Start page number
    :return: End page number
    """
    return (
        start_page_number + (total // page_size) + (1 if total % page_size else 0) - 1
    )


class BaseBilibiliSpider(Spider):
    response_model: typing.Type[models.BilibiliResponse] | None = None

    def before(self):
        pass

    def after(self):
        pass

    def get_items(self) -> typing.Iterable[BaseModel]:
        yield from self.get_items_from_response(self.send_request())

    def process_item(self, item: BaseModel, **kwargs) -> orm.DeclarativeBase:
        return self.database_model(
            **{
                **item.model_dump(),
                **kwargs,
            }
        )

    def send_request(
        self, method: str = "GET"
    ) -> models.BilibiliResponse | requests.Response:
        resp = requests.request(method, self.api, **self.get_request_args())
        resp.raise_for_status()
        return self.response_model(**resp.json()) if self.response_model else resp

    def get_request_args(self) -> dict:
        return {"headers": helper.user_agent_headers()}

    def get_items_from_response(
        self, response: models.BilibiliResponse
    ) -> typing.Iterable[BaseModel]:
        return response.data.list_data

    def save_to_db(self, items: typing.Iterable[BaseModel]):
        with Session() as s:
            self.recreate(items, session=s)
            s.commit()

    @abc.abstractmethod
    def recreate(self, items: typing.Iterable[BaseModel], session: sa.orm.Session):
        pass

    def run(self):
        self.before()
        self.save_to_db(self.get_items())
        self.after()


class PageSpider(BaseBilibiliSpider):
    default_page_size: int = 20
    default_page_number: int = 1

    def __init__(
        self,
        total: int,
        page_size: int = default_page_size,
        page_number: int = default_page_number,
    ):
        """
        :param total: Total number of items to be crawled
        :param page_size: Number of items per page
        :param page_number: Start page number
        """
        super().__init__()
        self.total = total
        self.page_size = page_size
        self.page_number = page_number
        self.end_page_number = calculate_end_page(total, page_size, page_number)

    def get_items(self) -> typing.Iterable[BaseModel]:
        count = 0
        while self.page_number <= self.end_page_number:
            response = self.send_request()
            for item in self.get_items_from_response(response):
                yield item
                count += 1
                if count >= self.total:
                    return
            self.page_number += 1

    @abc.abstractmethod
    def recreate(self, items: typing.Iterable[BaseModel], session: sa.orm.Session):
        raise NotImplementedError()


class SearchSpider(BaseBilibiliSpider):
    def __init__(self, **search_params):
        super().__init__()
        self.search_params = search_params

    def get_items(self) -> typing.Iterable[BaseModel]:
        yield from self.get_items_from_response(self.send_request())

    @abc.abstractmethod
    def recreate(self, items: typing.Iterable[BaseModel], session: sa.orm.Session):
        pass


class PopularSpider(PageSpider):
    api: str = "https://api.bilibili.com/x/web-interface/popular"
    name: str = "popular"
    database_model = db.BilibiliPopularVideos
    item_model = models.PopularVideoModel
    response_model = models.PopularResponse

    def get_request_args(self) -> dict:
        return {
            **super().get_request_args(),
            "params": {
                "pn": self.page_number,
                "ps": self.page_size,
            },
        }

    def recreate(self, items: typing.Iterable[BaseModel], session: sa.orm.Session):
        items = list(items)
        session.execute(
            sa.delete(self.database_model).where(
                self.database_model.bvid.in_([item.bvid for item in items]),
            )
        )
        session.add_all([self.process_item(item) for item in items])


class WeeklySpider(SearchSpider):
    api = "https://api.bilibili.com/x/web-interface/popular/series/one"
    api_list = "https://api.bilibili.com/x/web-interface/popular/series/list"
    name = "weekly"
    video_source = models.VideoSource.WEEKLY
    item_model = models.WeeklyVideoModel
    response_model = models.WeeklyResponse
    database_model = db.BilibiliWeeklyVideos

    search_key: str = "week"

    numbers_list: list[int] | None = None

    @cached_property
    def week(self) -> int:
        if self.search_key not in self.search_params:
            raise ValueError(f"search_key {self.search_key} not in search_params")
        return int(self.search_params[self.search_key])

    def get_request_args(self) -> dict:
        return {**super().get_request_args(), "params": {"number": self.week}}

    def recreate(self, items: typing.Iterable[BaseModel], session: sa.orm.Session):
        session.execute(
            sa.delete(self.database_model).where(
                self.database_model.week == self.week,
            )
        )
        session.add_all([self.process_item(item, week=self.week) for item in items])

    @classmethod
    def get_all_numbers(cls) -> list[int]:
        if cls.numbers_list is None:
            resp = requests.get(
                cls.api_list,
                headers={
                    **helper.user_agent_headers(),
                },
            )
            resp.raise_for_status()
            cls.numbers_list = [item["number"] for item in resp.json()["data"]["list"]]
        return cls.numbers_list


class PreciousSpider(PageSpider):
    api = "https://api.bilibili.com/x/web-interface/popular/precious"
    name = "precious"
    default_page_size = 100
    default_total = 100
    item_model = models.PreciousVideoModel
    response_model = models.PreciousResponse
    database_model = db.BilibiliPreciousVideos

    def __init__(
        self,
        total: int = default_total,
        page_size: int = default_page_size,
        page_number: int = 1,
    ):
        super().__init__(total, page_size, page_number)

    def get_request_args(self) -> dict:
        return {
            **super().get_request_args(),
            "params": {"page_size": self.page_size, "page": self.page_number},
        }

    def recreate(self, items: typing.Iterable[BaseModel], session: sa.orm.Session):
        session.execute(sa.delete(self.database_model))
        session.add_all([self.process_item(item) for item in items])


class RankSpider:
    pass


class MusicSpider:
    pass


class DramaSpider:
    pass


def run_spider(name: str, *args, **kwargs):
    try:
        spider = SPIDERS[name](*args, **kwargs)
    except KeyError as ke:
        print(f"spider not found: {ke.args[0]}")
        exit(1)
    spider.run()


if __name__ == "__main__":
    run_spider("popular", total=100)
    run_spider("weekly", week=239)
    run_spider("precious")
