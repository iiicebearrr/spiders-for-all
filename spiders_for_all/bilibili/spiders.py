from __future__ import annotations

import typing
import time
import hashlib
import random
from typing import TypeAlias
from functools import cached_property
from itertools import batched

import requests
import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy import orm

from spiders_for_all.bilibili import models
from spiders_for_all.bilibili import db
from spiders_for_all.core.base import SPIDERS, Spider, get_all_spiders
from spiders_for_all.utils import helper
from spiders_for_all.utils.logger import get_logger
from spiders_for_all.conf import settings

Session = db.Session

_BilibiliResponse: TypeAlias = (
    models.BilibiliPlayResponse | models.BilibiliVideoResponse
)
_BilibiliResponseTyped: TypeAlias = typing.Type[_BilibiliResponse]

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
    response_model: _BilibiliResponseTyped
    logger = logger
    insert_batch = 100

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

    def get_items(self) -> typing.Iterable[BaseModel]:
        """
        Get items from response
        :return: An iterable object of `pydantic.BaseModel`
        """
        yield from self.get_items_from_response(self.send_request())

    def process_item(self, item: BaseModel, **kwargs) -> orm.DeclarativeBase:
        """
        Create sqlalchemy model from pydantic model and kwargs
        :param item: item validated by pydantic model
        :param kwargs: extra kwargs to save to database
        :return:
        """
        return self.database_model(
            **{
                **item.model_dump(),
                **kwargs,
            }
        )

    def send_request(
        self, method: str = "GET"
    ) -> models.BilibiliVideoResponse | models.BilibiliPlayResponse:
        """
        Send request to api
        :param method: http method
        :return: A `pydantic.BaseModel` object
        """
        if not issubclass(self.response_model, models.BilibiliResponse):
            raise TypeError(
                f"{self.response_model} is not a valid response model, "
                f"should be a subclass of {models.BilibiliResponse}"
            )
        req_kwargs = self.get_request_args()
        self.debug(f"==> {method.upper()} {self.api}: {req_kwargs}")
        resp = requests.request(method, self.api, **req_kwargs)
        self.debug(f"<== {method.upper()} {resp.request.url}: {resp.status_code}")
        resp.raise_for_status()
        json_data = resp.json()
        self.debug(f"<== Response json: {json_data}")
        return self.response_model(**json_data)

    def get_request_args(self) -> dict:
        """
        Request kwargs to set
        """
        return {"headers": helper.user_agent_headers()}

    def get_items_from_response(
        self, response: _BilibiliResponse
    ) -> typing.Iterable[BaseModel]:
        """
        Get list data items from response model
        :param response:
        """
        response.raise_for_status()
        return response.data.list_data

    def save_to_db(self, items: typing.Iterable[BaseModel]):
        """
        Save items to database
        :param items: An iterable object of `pydantic.BaseModel`
        :return:
        """
        with Session() as s:
            for batch in batched(items, self.insert_batch):
                self.recreate(batch, session=s)
                self.info(f"Inserted {len(batch)} items")
            s.commit()

    def recreate(self, items: typing.Iterable[BaseModel], session: orm.Session):
        """
        Upsert/Recreate items to database
        :param items: items to be upserted
        :param session: sqlalchemy session object
        :return:
        """

        # TODO: Make truncate and upsert as options
        session.execute(sa.delete(self.database_model))
        session.add_all(map(self.process_item, items))

    def run(self):
        """
        Run the spider
        """
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
        sleep_before_next_request: float | int | tuple[int, int] | None = None,
    ):
        """
        :param total: Total number of items to be crawled
        :param page_size: Number of items per page
        :param page_number: Start page number
        """
        super().__init__()
        self.total = int(total)
        self.page_size = int(page_size)
        self.page_number = int(page_number)
        self.end_page_number = calculate_end_page(
            self.total, self.page_size, self.page_number
        )
        self.sleep_before_next_request = sleep_before_next_request

    def get_items(self) -> typing.Iterable[BaseModel]:
        """
        Get items by page
        :return:
        """
        count = 0
        while self.page_number <= self.end_page_number:
            # TODO: change page size dynamically instead of calculating `count`
            response = self.send_request()
            items = self.get_items_from_response(response)
            if not items:
                break
            for item in items:
                yield item
                count += 1
                if count >= self.total:
                    return
            if self.sleep_before_next_request is not None:
                time.sleep(random.randrange(2, 5))
            self.page_number += 1

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


class BaseSearchSpider(BaseBilibiliSpider):
    def __init__(self, **search_params):
        super().__init__()
        self.search_params = search_params


class PopularSpider(BasePageSpider):
    api: str = "https://api.bilibili.com/x/web-interface/popular"
    name: str = "popular"
    alias = "综合热门"
    database_model = db.BilibiliPopularVideos
    item_model = models.PopularVideoItem
    response_model = models.PopularResponse

    def get_request_args(self) -> dict:
        return {
            **super().get_request_args(),
            "params": {
                "pn": self.page_number,
                "ps": self.page_size,
            },
        }

    def recreate(self, items: typing.Iterable[BaseModel], session: orm.Session):
        items = list(items)
        session.execute(
            sa.delete(self.database_model).where(
                self.database_model.bvid.in_([item.bvid for item in items]),  # type: ignore
            )
        )
        session.add_all([self.process_item(item) for item in items])


class WeeklySpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/popular/series/one"
    api_list = "https://api.bilibili.com/x/web-interface/popular/series/list"
    name = "weekly"
    alias = "每周必看"
    item_model = models.WeeklyVideoItem
    response_model = models.WeeklyResponse
    database_model = db.BilibiliWeeklyVideos

    search_key: str = "week"

    numbers_list: list[int] | None = None

    @cached_property
    def week(self) -> int:
        # Use the latest week number if not specified
        if self.search_key not in self.search_params:
            self.get_all_numbers()
            return max(self.numbers_list)  # type: ignore
        return int(self.search_params[self.search_key])

    def get_request_args(self) -> dict:
        return {**super().get_request_args(), "params": {"number": self.week}}

    def recreate(self, items: typing.Iterable[BaseModel], session: orm.Session):
        session.execute(
            sa.delete(self.database_model).where(
                self.database_model.week == self.week,  # type: ignore
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


class PreciousSpider(BasePageSpider):
    api = "https://api.bilibili.com/x/web-interface/popular/precious"
    name = "precious"
    alias = "入站必刷"
    default_page_size = 100

    item_model = models.PreciousVideoItem
    response_model = models.PreciousResponse
    database_model = db.BilibiliPreciousVideos

    def get_request_args(self) -> dict:
        return {
            **super().get_request_args(),
            "params": {"page_size": self.page_size, "page": self.page_number},
        }


class RankAllSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
    name = "rank_all"
    alias = "全站"

    item_model = models.VideoItem
    database_model = db.BilibiliRankAll
    response_model = models.BilibiliVideoResponse


class RankDramaSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/web/rank/list?day=3&season_type=1"
    name = "rank_drama"
    alias = "番剧"

    item_model = models.PlayItem
    database_model = db.BilibiliRankDrama
    response_model = models.RankDramaResponse


class RankCnCartoonSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=4"
    name = "rank_cn_cartoon"
    alias = "国产动画"

    item_model = models.PlayItem
    database_model = db.BilibiliRankCnCartoon
    response_model = models.BilibiliPlayResponse


class RankCnRelatedSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=168&type=all"
    name = "rank_cn_related"
    alias = "国创相关"

    item_model = models.VideoItem
    database_model = db.BilibiliRankCnRelated
    response_model = models.BilibiliVideoResponse


class RankDocumentarySpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=3"
    name = "rank_documentary"
    alias = "纪录片"

    item_model = models.PlayItem
    database_model = db.BilibiliRankDocumentary
    response_model = models.BilibiliPlayResponse


class RankCartoonSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=1&type=all"
    name = "rank_cartoon"
    alias = "动画"

    item_model = models.VideoItem
    database_model = db.BilibiliRankCartoon
    response_model = models.BilibiliVideoResponse


class RankMusicSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=3&type=all"
    name = "rank_music"
    alias = "音乐"

    item_model = models.VideoItem
    database_model = db.BilibiliRankMusic
    response_model = models.BilibiliVideoResponse


class RankDanceSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=129&type=all"
    name = "rank_dance"
    alias = "舞蹈"

    item_model = models.VideoItem
    database_model = db.BilibiliRankDance
    response_model = models.BilibiliVideoResponse


class RankGameSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=4&type=all"
    name = "rank_game"
    alias = "游戏"

    item_model = models.VideoItem
    database_model = db.BilibiliRankGame
    response_model = models.BilibiliVideoResponse


class RankTechSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=188&type=all"
    name = "rank_tech"
    alias = "科技"

    item_model = models.VideoItem
    database_model = db.BilibiliRankTech
    response_model = models.BilibiliVideoResponse


class RankKnowledgeSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=36&type=all"
    name = "rank_knowledge"
    alias = "知识"

    item_model = models.VideoItem
    database_model = db.BilibiliRankKnowledge
    response_model = models.BilibiliVideoResponse


class RankSportSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=234&type=all"
    name = "rank_sport"
    alias = "运动"

    item_model = models.VideoItem
    database_model = db.BilibiliRankSport
    response_model = models.BilibiliVideoResponse


class RankCarSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=223&type=all"
    name = "rank_car"
    alias = "汽车"

    item_model = models.VideoItem
    database_model = db.BilibiliRankCar
    response_model = models.BilibiliVideoResponse


class RankLifeSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=160&type=all"
    name = "rank_life"
    alias = "生活"

    item_model = models.VideoItem
    database_model = db.BilibiliRankLife
    response_model = models.BilibiliVideoResponse


class RankFoodSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=211&type=all"
    name = "rank_food"
    alias = "美食"

    item_model = models.VideoItem
    database_model = db.BilibiliRankFood
    response_model = models.BilibiliVideoResponse


class RankAnimalSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=217&type=all"
    name = "rank_animal"
    alias = "动物圈"

    item_model = models.VideoItem
    database_model = db.BilibiliRankAnimal
    response_model = models.BilibiliVideoResponse


class RankAutoTuneSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=119&type=all"
    name = "rank_auto_tune"
    alias = "鬼畜"

    item_model = models.VideoItem
    database_model = db.BilibiliRankAuto
    response_model = models.BilibiliVideoResponse


class RankFashionSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=155&type=all"
    name = "rank_fashion"
    alias = "时尚"

    item_model = models.VideoItem
    database_model = db.BilibiliRankFashion
    response_model = models.BilibiliVideoResponse


class RankEntSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=5&type=all"
    name = "rank_ent"
    alias = "娱乐"

    item_model = models.VideoItem
    database_model = db.BilibiliRankEnt
    response_model = models.BilibiliVideoResponse


class RankFilmSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=181&type=all"
    name = "rank_film"
    alias = "影视"

    item_model = models.VideoItem
    database_model = db.BilibiliRankFilm
    response_model = models.BilibiliVideoResponse


class RankMovieSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=2"
    name = "rank_movie"
    alias = "电影"

    item_model = models.PlayItem
    database_model = db.BilibiliRankMovie
    response_model = models.BilibiliPlayResponse


class RankTvSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=5"
    name = "rank_tv"
    alias = "电视剧"

    item_model = models.PlayItem
    database_model = db.BilibiliRankTv
    response_model = models.BilibiliPlayResponse


class RankVarietySpider(BaseSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=7"
    name = "rank_variety"
    alias = "综艺"

    item_model = models.PlayItem
    database_model = db.BilibiliRankVariety
    response_model = models.BilibiliPlayResponse


class RankOriginSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=origin"
    name = "rank_origin"
    alias = "原创"

    item_model = models.VideoItem
    database_model = db.BilibiliRankOrigin
    response_model = models.BilibiliVideoResponse


class RankNewSpider(BaseSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=rookie"
    name = "rank_new"
    alias = "新人"

    item_model = models.VideoItem
    database_model = db.BilibiliRankNew
    response_model = models.BilibiliVideoResponse


class AuthorSpider(BasePageSpider):
    api = "https://api.bilibili.com/x/space/wbi/arc/search"
    api_get_nav_num = "https://api.bilibili.com/x/space/navnum"
    api_get_nav = "https://api.bilibili.com/x/web-interface/nav"
    name = "author"
    alias = "up主"

    response_model = models.AuthorVideoResponse
    database_model = db.BilibiliAuthorVideo
    item_model = models.AuthorVideoItem

    encrypt_string_fmt = "dm_cover_img_str={dm_cover_img_str}&dm_img_list=%5B%5D&dm_img_str={dm_img_str}&keyword=&mid={mid}&order=pubdate&order_avoided=true&platform=web&pn={pn}&ps={ps}&tid=&web_location="

    def __init__(
        self,
        mid: int,
        total: int | None = None,
        sess_data: str | None = None,
        page_size: int = 30,
        page_number: int = 1,
    ):
        self.mid = mid

        self.sess_data = sess_data

        self.wbi_info = self.get_wbi_info()

        self.key = self.get_mixin_key(self.wbi_info.img_key + self.wbi_info.sub_key)

        total = (
            self.get_total(self.mid)
            if total is None
            else min(int(total), self.get_total(self.mid))
        )

        super().__init__(
            total=total,
            page_size=page_size,
            page_number=page_number,
            sleep_before_next_request=(5, 10),
        )

    def get_wbi_info(self) -> models.WbiInfo:
        resp = requests.get(
            self.api_get_nav,
            headers=helper.user_agent_headers(),
        )

        resp.raise_for_status()

        wbi_img = resp.json().get("data", {}).get("wbi_img", None)

        if wbi_img is None:
            raise ValueError("wbi_img not found")

        return models.WbiInfo(**wbi_img)

    def get_mixin_key(self, e: str) -> str:
        indices = [
            46,
            47,
            18,
            2,
            53,
            8,
            23,
            32,
            15,
            50,
            10,
            31,
            58,
            3,
            45,
            35,
            27,
            43,
            5,
            49,
            33,
            9,
            42,
            19,
            29,
            28,
            14,
            39,
            12,
            38,
            41,
            13,
            37,
            48,
            7,
            16,
            24,
            55,
            40,
            61,
            26,
            17,
            0,
            1,
            60,
            51,
            30,
            4,
            22,
            25,
            54,
            21,
            56,
            59,
            6,
            63,
            57,
            62,
            11,
            36,
            20,
            34,
            44,
            52,
        ]
        result = []
        for r in indices:
            if r < len(e):
                result.append(e[r])
        return "".join(result)[:32]

    def get_total(self, mid: int) -> int:
        resp = requests.get(
            self.api_get_nav_num,
            params={"mid": mid},
            headers=helper.user_agent_headers(),
        )
        resp.raise_for_status()
        total = resp.json().get("data", {}).get("video", None)
        if total is None:
            raise ValueError(f"mid {mid} info not found")
        return total

    def get_items_from_response(
        self,
        # TODO: fix mypy error
        response: models.AuthorVideoResponse,  # type: ignore
    ) -> typing.Iterable[models.AuthorVideoItem]:
        response.raise_for_status()
        return response.data.list_data.items

    def get_wrid(self, params: str) -> str:
        md5 = hashlib.md5()

        md5.update(
            (params + self.key).encode(),
        )

        return md5.hexdigest()

    def get_request_args(self) -> dict:
        wts = round(time.time())

        params = self.encrypt_string_fmt.format(
            mid=self.mid,
            ps=self.page_size,
            pn=self.page_number,
            dm_img_str=settings.BILIBILI_PARAM_DM_IMG_STR,
            dm_cover_img_str=settings.BILIBILI_PARAM_DM_COVER_IMG_STR,
        )

        wrid = self.get_wrid(params + f"&wts={wts}")

        params = "&".join([params, f"w_rid={wrid}", f"wts={wts}"])

        kwargs = super().get_request_args()

        # NOTE: Not sure if this will work
        kwargs["headers"]["accept-language"] = "en,zh-CN;q=0.9,zh;q=0.8"

        if self.sess_data is not None:
            kwargs["cookies"] = {"SESSDATA": self.sess_data}

        return {
            **kwargs,
            "params": params,
        }

    def recreate(self, items: typing.Iterable[BaseModel], session: orm.Session):
        items = list(items)
        session.execute(
            sa.delete(self.database_model).where(
                self.database_model.bvid.in_([item.bvid for item in items]),  # type: ignore
            )
        )
        session.add_all([self.process_item(item) for item in items])


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
