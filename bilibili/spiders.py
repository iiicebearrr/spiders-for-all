import abc
import typing
import requests
import sqlalchemy as sa
from sqlalchemy import orm
from bilibili import models
from bilibili import db
from pydantic import BaseModel
from utils import helper

Session = db.Session


class Spider(abc.ABC):
    @abc.abstractmethod
    def run(self, *args, **kwargs):
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


class BilibiliSpider(Spider):
    api: str
    name: str

    database_model: typing.Type[orm.DeclarativeBase]
    pydantic_model: typing.Type[BaseModel]
    response_model: typing.Type[BaseModel] | None = None

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
        self.total = total
        self.page_size = page_size
        self.page_number = page_number
        self.end_page_number = calculate_end_page(total, page_size, page_number)
        if not all([self.database_model, self.pydantic_model, self.response_model]):
            # ? Maybe let these three params be optional
            raise ValueError(
                "db_model, pydantic_model, response_model must be set before init"
            )

    def clear(self):
        """Truncate table every time"""
        with Session() as s:
            s.execute(sa.delete(self.database_model))
            s.commit()

    def get_items(self) -> typing.Iterable[BaseModel]:
        """Get items from API"""
        count = 0
        while self.page_number <= self.end_page_number:
            response = self.send_request()
            for item in self.get_items_from_response(response):
                yield item
                count += 1
                if count >= self.total:
                    return
            self.page_number += 1

    def process_item(self, item: BaseModel) -> orm.DeclarativeBase:
        """Process item"""
        return self.database_model(**item.model_dump())

    def send_request(self, method: str = "GET") -> BaseModel | requests.Response:
        """Send request"""
        resp = requests.request(method, self.api, **self.get_request_args())
        resp.raise_for_status()
        return self.response_model(**resp.json()) if self.response_model else resp

    def get_request_args(self) -> dict:
        """Get request args"""
        return {"headers": helper.user_agent_headers()}

    @abc.abstractmethod
    def get_items_from_response(
        self, response: requests.Response
    ) -> typing.Iterable[BaseModel]:
        """Get items from response"""
        pass

    def save_to_db(self, items: typing.Iterable[BaseModel]):
        """Save items to database"""
        with Session() as s:
            s.add_all([self.process_item(item) for item in items])
            s.commit()

    def run(self, *args, **kwargs):
        self.clear()
        self.save_to_db(self.get_items())


class PopularSpider(BilibiliSpider):
    api: str = "https://api.bilibili.com/x/web-interface/popular"
    name: str = "popular"
    database_model = db.BilibiliPopularVideos
    pydantic_model = models.PydanticBilibiliPopularVideo
    response_model = models.BilibiliResponse

    def get_request_args(self) -> dict:
        return {
            **super().get_request_args(),
            "params": {
                "pn": self.page_number,
                "ps": self.page_size,
            },
        }

    def get_items_from_response(
        self, response: models.BilibiliResponse
    ) -> typing.Iterable[BaseModel]:
        return response.data.list_data


#
# class WeeklySpider(BilibiliSpider):
#     def __init__(self, num: int):
#         self.num = num
#         super().__init__(num)


if __name__ == "__main__":
    spider = PopularSpider(1)
    spider.run()
