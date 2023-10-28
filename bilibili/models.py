from __future__ import annotations

import typing

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_serializer
from enum import Enum


class BilibiliResponse(BaseModel):
    """Base response model of bilibili api"""

    code: int
    data: BilibiliResponseData
    message: str | None
    ttl: int


class PopularResponse(BilibiliResponse):
    """Response model of bilibili popular api"""

    data: PopularData


class WeeklyResponse(BilibiliResponse):
    """Response model of bilibili weekly api"""

    data: WeeklyData


class BilibiliResponseData(BaseModel):
    """Base data model of bilibili api"""

    list_data: list[VideoModel] = Field([], validation_alias="list")


class PopularData(BilibiliResponseData):
    """Data model of bilibili popular api"""

    no_more: bool
    list_data: list[PopularVideoModel] = Field([], validation_alias="list")


class WeeklyData(BilibiliResponseData):
    """Data model of bilibili weekly api"""

    config: dict[str, typing.Any]
    reminder: str
    list_data: list[WeeklyVideoModel] = Field([], validation_alias="list")


class VideoOwner(BaseModel):
    mid: int
    name: str
    face: str


class RecommendReason(BaseModel):
    content: str
    corner_mark: int


class VideoStat(BaseModel):
    aid: int
    coin: int
    danmaku: int
    dislike: int
    favorite: int
    his_rank: int
    like: int
    now_rank: int
    reply: int
    share: int
    view: int


class VideoModel(BaseModel):
    aid: int
    bvid: str
    cid: int
    copyright: int
    desc: str
    duration: int
    dynamic: str
    enable_vt: bool
    first_frame: str | None = None
    is_ogv: int
    mission_id: int | None = None
    owner: VideoOwner
    pic: str
    pub_location: str
    pubdate: int
    rcmd_reason: RecommendReason
    season_type: int
    short_link_v2: str
    stat: VideoStat
    state: int
    tid: int
    title: str
    tname: str
    videos: int

    @field_serializer("owner", "rcmd_reason", "stat")
    def to_string(self, value: BaseModel) -> str:
        return value.model_dump_json() if isinstance(value, BaseModel) else value


class PopularVideoModel(VideoModel):
    pass


class WeeklyVideoModel(VideoModel):
    rcmd_reason: str


class VideoSource(Enum):
    POPULAR = 0
    WEEKLY = 1
    HISTORY = 2
    RANK = 3
    MUSIC = 4
    DRAMA = 5
    SEARCH = 6
