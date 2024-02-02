from __future__ import annotations

import hashlib
import random
import time
import typing
import urllib.parse
from logging import Logger
from typing import Iterable

import requests
from pydantic import BaseModel

from spiders_for_all.conf import settings
from spiders_for_all.core import spider
from spiders_for_all.core.spider import (
    DbActionOnInit,
    DbActionOnSave,
    RateLimitMixin,
    SleepInterval,
)
from spiders_for_all.spiders.bilibili import db, models, schema
from spiders_for_all.utils.logger import get_logger

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


def check_response_352(response: requests.Response, *args, **kwargs):
    response.raise_for_status()
    code = response.json().get("code")
    if code != 0:
        raise ValueError(
            f"Response failed with code: {code}. Message: {response.json().get('message')}"
        )


class BaseBilibiliSpider(spider.BaseSpider):
    platform = "bilibili"
    response_model: typing.Type[models.BilibiliResponse] | None
    logger = logger
    session_manager = db.SessionManager

    def get_items_from_response(
        self,
        response: models.BilibiliResponse,  # type: ignore
    ) -> typing.Iterable[BaseModel]:
        return response.data.list_data

    def request_items(self, method: str, url: str, **kwargs):
        kwargs["hooks"] = {"response": check_response_352}
        return super().request_items(method, url, **kwargs)


class BaseBilibiliPageSpider(BaseBilibiliSpider, spider.PageSpider):
    pass


class BaseBilibiliSearchSpider(BaseBilibiliSpider, spider.SearchSpider):
    pass


class PopularSpider(BaseBilibiliPageSpider):
    api: str = "https://api.bilibili.com/x/web-interface/popular"
    name: str = "popular"
    alias = "综合热门"
    database_model = schema.BilibiliPopularVideos
    item_model = models.PopularVideoItem
    response_model = models.PopularResponse

    page_field = "pn"
    page_size_field = "ps"

    db_action_on_save = spider.DbActionOnSave.UPDATE_OR_CREATE


# TODO: Weekly api now need w_rid
# class WeeklySpider(BaseBilibiliSearchSpider):
#     api = "https://api.bilibili.com/x/web-interface/popular/series/one"
#     api_list = "https://api.bilibili.com/x/web-interface/popular/series/list"
#     name = "weekly"
#     alias = "每周必看"
#     item_model = models.WeeklyVideoItem
#     response_model = models.WeeklyResponse
#     database_model = schema.BilibiliWeeklyVideos

#     search_key: str = "week"

#     numbers_list: list[int] | None = None

#     db_action_on_save = spider.DbActionOnSave.UPDATE_OR_CREATE

#     @cached_property
#     def week(self) -> int:
#         # Use the latest week number if not specified
#         if self.search_key not in self.kwargs:
#             self.get_all_numbers()
#             return max(self.numbers_list)  # type: ignore
#         return int(self.kwargs[self.search_key])

#     def get_request_args(self) -> dict:
#         return {**super().get_request_args(), "params": {"number": self.week}}

#     def item_to_dict(self, item: BaseModel, **extra) -> dict:
#         return super().item_to_dict(item, week=self.week, **extra)

#     @classmethod
#     def get_all_numbers(cls) -> list[int]:
#         if cls.numbers_list is None:
#             with client.HttpClient(logger=cls.logger) as c:
#                 resp = c.get(cls.api_list)
#                 cls.numbers_list = [
#                     item["number"] for item in resp.json()["data"]["list"]
#                 ]
#         return cls.numbers_list


class PreciousSpider(BaseBilibiliPageSpider):
    api = "https://api.bilibili.com/x/web-interface/popular/precious"
    name = "precious"
    alias = "入站必刷"
    default_page_size = 100

    item_model = models.PreciousVideoItem
    response_model = models.PreciousResponse
    database_model = schema.BilibiliPreciousVideos

    def get_request_args(self) -> dict:
        return {
            **super().get_request_args(),
            "params": {"page_size": self.page_size, "page": self.page_number},
        }


class RankAllSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
    name = "rank_all"
    alias = "全站"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankAll
    response_model = models.BilibiliVideoResponse


class RankDramaSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/pgc/web/rank/list?day=3&season_type=1"
    name = "rank_drama"
    alias = "番剧"

    item_model = models.PlayItem
    database_model = schema.BilibiliRankDrama
    response_model = models.RankDramaResponse


class RankCnCartoonSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=4"
    name = "rank_cn_cartoon"
    alias = "国产动画"

    item_model = models.PlayItem
    database_model = schema.BilibiliRankCnCartoon
    response_model = models.BilibiliPlayResponse


class RankCnRelatedSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=168&type=all"
    name = "rank_cn_related"
    alias = "国创相关"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankCnRelated
    response_model = models.BilibiliVideoResponse


class RankDocumentarySpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=3"
    name = "rank_documentary"
    alias = "纪录片"

    item_model = models.PlayItem
    database_model = schema.BilibiliRankDocumentary
    response_model = models.BilibiliPlayResponse


class RankCartoonSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=1&type=all"
    name = "rank_cartoon"
    alias = "动画"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankCartoon
    response_model = models.BilibiliVideoResponse


class RankMusicSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=3&type=all"
    name = "rank_music"
    alias = "音乐"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankMusic
    response_model = models.BilibiliVideoResponse


class RankDanceSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=129&type=all"
    name = "rank_dance"
    alias = "舞蹈"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankDance
    response_model = models.BilibiliVideoResponse


class RankGameSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=4&type=all"
    name = "rank_game"
    alias = "游戏"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankGame
    response_model = models.BilibiliVideoResponse


class RankTechSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=188&type=all"
    name = "rank_tech"
    alias = "科技"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankTech
    response_model = models.BilibiliVideoResponse


class RankKnowledgeSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=36&type=all"
    name = "rank_knowledge"
    alias = "知识"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankKnowledge
    response_model = models.BilibiliVideoResponse


class RankSportSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=234&type=all"
    name = "rank_sport"
    alias = "运动"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankSport
    response_model = models.BilibiliVideoResponse


class RankCarSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=223&type=all"
    name = "rank_car"
    alias = "汽车"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankCar
    response_model = models.BilibiliVideoResponse


class RankLifeSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=160&type=all"
    name = "rank_life"
    alias = "生活"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankLife
    response_model = models.BilibiliVideoResponse


class RankFoodSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=211&type=all"
    name = "rank_food"
    alias = "美食"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankFood
    response_model = models.BilibiliVideoResponse


class RankAnimalSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=217&type=all"
    name = "rank_animal"
    alias = "动物圈"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankAnimal
    response_model = models.BilibiliVideoResponse


class RankAutoTuneSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=119&type=all"
    name = "rank_auto_tune"
    alias = "鬼畜"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankAuto
    response_model = models.BilibiliVideoResponse


class RankFashionSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=155&type=all"
    name = "rank_fashion"
    alias = "时尚"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankFashion
    response_model = models.BilibiliVideoResponse


class RankEntSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=5&type=all"
    name = "rank_ent"
    alias = "娱乐"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankEnt
    response_model = models.BilibiliVideoResponse


class RankFilmSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=181&type=all"
    name = "rank_film"
    alias = "影视"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankFilm
    response_model = models.BilibiliVideoResponse


class RankMovieSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=2"
    name = "rank_movie"
    alias = "电影"

    item_model = models.PlayItem
    database_model = schema.BilibiliRankMovie
    response_model = models.BilibiliPlayResponse


class RankTvSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=5"
    name = "rank_tv"
    alias = "电视剧"

    item_model = models.PlayItem
    database_model = schema.BilibiliRankTv
    response_model = models.BilibiliPlayResponse


class RankVarietySpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/pgc/season/rank/web/list?day=3&season_type=7"
    name = "rank_variety"
    alias = "综艺"

    item_model = models.PlayItem
    database_model = schema.BilibiliRankVariety
    response_model = models.BilibiliPlayResponse


class RankOriginSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=origin"
    name = "rank_origin"
    alias = "原创"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankOrigin
    response_model = models.BilibiliVideoResponse


class RankNewSpider(BaseBilibiliSearchSpider):
    api = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=rookie"
    name = "rank_new"
    alias = "新人"

    item_model = models.VideoItem
    database_model = schema.BilibiliRankNew
    response_model = models.BilibiliVideoResponse


class AuthorSpider(BaseBilibiliPageSpider):
    api = "https://api.bilibili.com/x/space/wbi/arc/search"
    api_get_nav_num = "https://api.bilibili.com/x/space/navnum"
    api_get_nav = "https://api.bilibili.com/x/web-interface/nav"
    name = "author"
    alias = "up主"

    response_model = models.AuthorVideoResponse
    database_model = schema.BilibiliAuthorVideo
    item_model = models.AuthorVideoItem

    db_action_on_save = spider.DbActionOnSave.UPDATE_OR_CREATE

    def __init__(
        self,
        mid: int,
        total: int | None = None,
        sess_data: str | None = None,
        page_size: int = 30,
        page_number: int = 1,
        record: bool = False,
    ):
        super().__init__(
            total=total,
            page_size=page_size,
            start_page_number=page_number,
            sleep_before_next_request=(5, 11),
        )

        self.record = record

        # Record all the bvid when crawling, for later use
        self.bvid_list_record = []

        self.client.headers.update(
            {
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )

        if sess_data:
            self.client.set_cookies("SESSDATA", sess_data)

        self.mid = mid

        self.sess_data = sess_data

        self.wbi_info = self.get_wbi_info()

        self.key = self.get_mixin_key(self.wbi_info.img_key + self.wbi_info.sub_key)

    def get_wbi_info(self) -> models.WbiInfo:
        with self.client.new() as c:
            resp = c.get(self.api_get_nav)

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

    def get_items_from_response(
        self,
        response: models.AuthorVideoResponse,  # type: ignore
    ) -> typing.Iterable[models.AuthorVideoItem]:
        response.raise_for_status()
        ret = response.data.list_data.items
        if self.record:
            self.bvid_list_record.extend([item.bvid for item in ret])
        return ret

    def get_wrid(self, params: str) -> str:
        return hashlib.md5((params + self.key).encode()).hexdigest()

    def get_request_args(self) -> dict:
        wts = round(time.time())

        dm_rand = "ABCDEFGHIJK"
        dm_img_list = "[]"
        dm_img_str = "".join(random.sample(dm_rand, 2))
        dm_cover_img_str = "".join(random.sample(dm_rand, 2))
        dm_img_inter = '{"ds":[],"wh":[0,0,0],"of":[0,0,0]}'

        params = {
            "mid": self.mid,
            "ps": self.page_size,
            "tid": 0,
            "pn": self.page_number,
            "keyword": "",
            "order": "pubdate",
            "platform": "web",
            "web_location": "",
            "dm_img_list": dm_img_list,
            "dm_img_str": dm_img_str,
            "dm_cover_img_str": dm_cover_img_str,
            "dm_img_inter": dm_img_inter,
            "wts": wts,
        }

        params = dict(sorted(params.items()))

        query = urllib.parse.urlencode(params)

        wrid = self.get_wrid(query)

        params["w_rid"] = wrid

        return {
            "params": params,
        }

    def get_record_bvid_list(self) -> list[str]:
        if self.record:
            return (
                self.bvid_list_record
                if self.total is None
                else self.bvid_list_record[: self.total]
            )
        return []


class AuthorFeedSpaceSpider(BaseBilibiliSpider, RateLimitMixin):
    api = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space"
    api_get_buvid3 = "https://api.bilibili.com/x/frontend/finger/spi"
    api_activate_buvid3 = (
        "https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi"
    )
    name = "feed"
    alias = "up主动态"

    db_action_on_save = spider.DbActionOnSave.UPDATE_OR_CREATE

    response_model = models.FeedResponse
    database_model = schema.BilibiliAuthorFeed
    item_model = models.FeedItem

    def __init__(
        self,
        mid: str,
        *args,
        logger: Logger | None = None,
        sleep_before_next_request: SleepInterval | None = None,
        db_action_on_init: DbActionOnInit | None = None,
        db_action_on_save: DbActionOnSave | None = None,
        **kwargs,
    ):
        self.mid = mid
        self.sess_data = settings.BILIBILI_COOKIE_SESS_DATA
        if self.sess_data is None:
            raise ValueError("sess_data is required for this spider.")
        super().__init__(
            *args,
            logger=logger,
            db_action_on_init=db_action_on_init,
            db_action_on_save=db_action_on_save,
            **kwargs,
        )
        self.offset: str = ""
        self.sleep_before_next_request = sleep_before_next_request
        self.client.set_cookies(
            "SESSDATA",
            self.sess_data,
        )

    def get_items_from_response(
        self, response: models.FeedResponse
    ) -> Iterable[BaseModel]:
        self.response = response
        return response.data.items

    def get_items(self) -> Iterable[models.FeedItem]:
        has_more = True

        while has_more:
            for item in self._get_items():  # type: ignore
                item: models.FeedItem
                yield item

                author_action = item.modules.module_author.author_action
                pub_time = item.modules.module_author.pub_time
                desc = self.get_feed_text(item)
                self.client.info(
                    f"{author_action} at {pub_time}{'.'if not desc else ': ' +desc}"
                )
            self.response: models.FeedResponse
            has_more = self.response.data.has_more
            self.offset = self.response.data.offset
            if has_more:
                self.sleep(self.sleep_before_next_request)

    def get_feed_text(self, item: models.FeedItem) -> str | None:
        desc = item.modules.module_dynamic.desc
        if desc is not None:
            desc = desc.text
        return desc

    def item_to_dict(self, item: models.FeedItem, **extra) -> dict:
        return {
            "id_str": item.id_str,
            "pub_time": item.modules.module_author.pub_time,
            "action": item.modules.module_author.author_action,
            "jump_url": item.modules.module_author.jump_url,
            "desc": self.get_feed_text(item),
            "comment": item.modules.module_stat.comment.count,
            "like": item.modules.module_stat.like.count,
            "forward": item.modules.module_stat.forward.count,
        }

    def get_request_args(self) -> dict:
        params = {
            "offset": self.offset,
            "host_mid": self.mid,
            "timezone_offset": -480,
            "platform": "web",
            "web_location": "",
            "features": "itemOpusStyle,listOnlyfans,opusBigCover,onlyfansVote",
        }

        return {"params": params}
