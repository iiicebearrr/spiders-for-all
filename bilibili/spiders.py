from __future__ import annotations

import typing
from functools import cached_property
from itertools import batched

import requests
import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy import orm

from bilibili import db
from bilibili import models
from core.base import SPIDERS
from core.base import Spider
from core.base import get_all_spiders
from utils import helper
from utils.logger import get_logger

Session = db.Session

logger = get_logger("bilibili")


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
    response_model: typing.Type[models.BilibiliVideoResponse] | None = None
    logger = logger
    insert_batch = 100

    def before(self):
        self.info(f"[{'Start':^10}]: {self.name}[{self.alias}]")

    def after(self):
        self.info(f"[{'Finished':^10}]: {self.name}[{self.alias}]")

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
    ) -> models.BilibiliVideoResponse | requests.Response:
        req_kwargs = self.get_request_args()
        self.debug(f"==> {method.upper()} {self.api}: {req_kwargs}")
        resp = requests.request(method, self.api, **req_kwargs)
        self.debug(f"<== {method.upper()} {self.api}: {resp.status_code}")
        resp.raise_for_status()
        json_data = resp.json()
        self.debug(f"<== Response json: {json_data}")
        return self.response_model(**json_data) if self.response_model else resp

    def get_request_args(self) -> dict:
        return {"headers": helper.user_agent_headers()}

    def get_items_from_response(
        self, response: models.BilibiliVideoResponse
    ) -> typing.Iterable[BaseModel]:
        return response.data.list_data

    def save_to_db(self, items: typing.Iterable[BaseModel]):
        with Session() as s:
            for batch in batched(items, self.insert_batch):
                self.recreate(batch, session=s)
                self.info(f"Inserted {len(batch)} items")
            s.commit()

    def recreate(self, items: typing.Iterable[BaseModel], session: sa.orm.Session):
        session.execute(sa.delete(self.database_model))
        session.add_all(map(self.process_item, items))

    def run(self):
        self.before()
        self.save_to_db(self.get_items())
        self.after()


class BasePageSpider(BaseBilibiliSpider):
    default_page_size: int = 20
    default_page_number: int = 1
    default_total: int = 100

    def __init__(
        self,
        total: int = default_total,
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


class BaseSearchSpider(BaseBilibiliSpider):
    def __init__(self, **search_params):
        super().__init__()
        self.search_params = search_params

    def get_items(self) -> typing.Iterable[BaseModel]:
        yield from self.get_items_from_response(self.send_request())


class PopularSpiderBase(BasePageSpider):
    api: str = "https://api.bilibili.com/x/web-interface/popular"
    name: str = "popular"
    alias = "综合热门"
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


class WeeklySpiderBase(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/popular/series/one"
    api_list = "https://api.bilibili.com/x/web-interface/popular/series/list"
    name = "weekly"
    alias = "每周必看"
    video_source = models.VideoSource.WEEKLY
    item_model = models.WeeklyVideoModel
    response_model = models.WeeklyResponse
    database_model = db.BilibiliWeeklyVideos

    search_key: str = "week"

    numbers_list: list[int] | None = None

    @cached_property
    def week(self) -> int:
        if self.search_key not in self.search_params:
            self.get_all_numbers()
            return max(self.numbers_list)
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


class PreciousSpiderBase(BasePageSpider):
    api = "https://api.bilibili.com/x/web-interface/popular/precious"
    name = "precious"
    alias = "入站必刷"
    default_page_size = 100

    item_model = models.PreciousVideoModel
    response_model = models.PreciousResponse
    database_model = db.BilibiliPreciousVideos

    def get_request_args(self) -> dict:
        return {
            **super().get_request_args(),
            "params": {"page_size": self.page_size, "page": self.page_number},
        }

    def recreate(self, items: typing.Iterable[BaseModel], session: sa.orm.Session):
        session.execute(sa.delete(self.database_model))
        session.add_all([self.process_item(item) for item in items])


class RankAllSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
    name = "rank_all"
    alias = "全站"

    item_model = models.VideoModel
    database_model = db.BilibiliRankAll
    response_model = models.BilibiliVideoResponse


class RankDramaSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/web/rank/list?day=3&season_type=1"
    name = "rank_drama"
    alias = "番剧"

    item_model = models.PlayModel
    database_model = db.BilibiliRankDrama
    response_model = models.RankDramaResponse


class RankCnCartoonSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=4"
    name = "rank_cn_cartoon"
    alias = "国产动画"

    item_model = models.PlayModel
    database_model = db.BilibiliRankCnCartoon
    response_model = models.BilibiliPlayResponse


class RankCnRelatedSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=168&type=all"
    name = "rank_cn_related"
    alias = "国创相关"

    item_model = models.VideoModel
    database_model = db.BilibiliRankCnRelated
    response_model = models.BilibiliVideoResponse


class RankDocumentarySpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=3"
    name = "rank_documentary"
    alias = "纪录片"

    item_model = models.PlayModel
    database_model = db.BilibiliRankDocumentary
    response_model = models.BilibiliPlayResponse


class RankCartoonSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=1&type=all"
    name = "rank_cartoon"
    alias = "动画"

    item_model = models.VideoModel
    database_model = db.BilibiliRankCartoon
    response_model = models.BilibiliVideoResponse


class RankMusicSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=3&type=all"
    name = "rank_music"
    alias = "音乐"

    item_model = models.VideoModel
    database_model = db.BilibiliRankMusic
    response_model = models.BilibiliVideoResponse


class RankDanceSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=129&type=all"
    name = "rank_dance"
    alias = "舞蹈"

    item_model = models.VideoModel
    database_model = db.BilibiliRankDance
    response_model = models.BilibiliVideoResponse


class RankGameSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=4&type=all"
    name = "rank_game"
    alias = "游戏"

    item_model = models.VideoModel
    database_model = db.BilibiliRankGame
    response_model = models.BilibiliVideoResponse


class RankTechSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=188&type=all"
    name = "rank_tech"
    alias = "科技"

    item_model = models.VideoModel
    database_model = db.BilibiliRankTech
    response_model = models.BilibiliVideoResponse


class RankKnowledgeSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=36&type=all"
    name = "rank_knowledge"
    alias = "知识"

    item_model = models.VideoModel
    database_model = db.BilibiliRankKnowledge
    response_model = models.BilibiliVideoResponse


class RankSportSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=234&type=all"
    name = "rank_sport"
    alias = "运动"

    item_model = models.VideoModel
    database_model = db.BilibiliRankSport
    response_model = models.BilibiliVideoResponse


class RankCarSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=223&type=all"
    name = "rank_car"
    alias = "汽车"

    item_model = models.VideoModel
    database_model = db.BilibiliRankCar
    response_model = models.BilibiliVideoResponse


class RankLifeSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=160&type=all"
    name = "rank_life"
    alias = "生活"

    item_model = models.VideoModel
    database_model = db.BilibiliRankLife
    response_model = models.BilibiliVideoResponse


class RankFoodSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=211&type=all"
    name = "rank_food"
    alias = "美食"

    item_model = models.VideoModel
    database_model = db.BilibiliRankFood
    response_model = models.BilibiliVideoResponse


class RankAnimalSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=217&type=all"
    name = "rank_animal"
    alias = "动物圈"

    item_model = models.VideoModel
    database_model = db.BilibiliRankAnimal
    response_model = models.BilibiliVideoResponse


class RankAutoTuneSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=119&type=all"
    name = "rank_auto_tune"
    alias = "鬼畜"

    item_model = models.VideoModel
    database_model = db.BilibiliRankAuto
    response_model = models.BilibiliVideoResponse


class RankFashionSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=155&type=all"
    name = "rank_fashion"
    alias = "时尚"

    item_model = models.VideoModel
    database_model = db.BilibiliRankFashion
    response_model = models.BilibiliVideoResponse


class RankEntSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=5&type=all"
    name = "rank_ent"
    alias = "娱乐"

    item_model = models.VideoModel
    database_model = db.BilibiliRankEnt
    response_model = models.BilibiliVideoResponse


class RankFilmSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=181&type=all"
    name = "rank_film"
    alias = "影视"

    item_model = models.VideoModel
    database_model = db.BilibiliRankFilm
    response_model = models.BilibiliVideoResponse


class RankMovieSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=2"
    name = "rank_movie"
    alias = "电影"

    item_model = models.PlayModel
    database_model = db.BilibiliRankMovie
    response_model = models.BilibiliPlayResponse


class RankTvSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=5"
    name = "rank_tv"
    alias = "电视剧"

    item_model = models.PlayModel
    database_model = db.BilibiliRankTv
    response_model = models.BilibiliPlayResponse


class RankVarietySpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=7"
    name = "rank_variety"
    alias = "综艺"

    item_model = models.PlayModel
    database_model = db.BilibiliRankVariety
    response_model = models.BilibiliPlayResponse


class RankOriginSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=origin"
    name = "rank_origin"
    alias = "原创"

    item_model = models.VideoModel
    database_model = db.BilibiliRankOrigin
    response_model = models.BilibiliVideoResponse


class RankNewSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=rookie"
    name = "rank_new"
    alias = "新人"

    item_model = models.VideoModel
    database_model = db.BilibiliRankNew
    response_model = models.BilibiliVideoResponse


def run_spider(name: str, *args, **kwargs):
    try:
        spider = SPIDERS[name](*args, **kwargs)
    except KeyError as ke:
        print(f"spider not found: {ke.args[0]}")
        exit(1)
    spider.run()


if __name__ == "__main__":
    spiders = get_all_spiders()
    for spider_cls, spider_item in spiders.items():
        _spider = spider_cls()
        _spider.run()
