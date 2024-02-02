from __future__ import annotations

import typing
from enum import Enum
from functools import cached_property

from pydantic import BaseModel, Field, HttpUrl, conlist, field_serializer

from spiders_for_all.core.response import Response


class BilibiliResponse(Response):
    code: int
    data: typing.Any
    message: str | None = None

    def raise_for_status(self) -> None:
        if self.code != 0:
            raise ValueError(
                f"Response failed with code: {self.code}. Message: {self.message}"
            )


class BilibiliVideoResponse(BilibiliResponse):
    """Base response model of bilibili api with video data return"""

    data: BilibiliVideoResponseData


class BilibiliPlayResponse(BilibiliResponse):
    """Base response model of bilibili api with play data return"""

    data: BilibiliPlayResponseData


class BilibiliVideoResponseData(BaseModel):
    """Base data model of bilibili api"""

    list_data: typing.Sequence[VideoItem] = Field([], validation_alias="list")


class BilibiliPlayResponseData(BaseModel):
    list_data: typing.Sequence[PlayItem] = Field([], validation_alias="list")


class RankDramaResponse(BilibiliPlayResponse):
    data: RankDramaData = Field(..., validation_alias="result")


class PopularResponse(BilibiliVideoResponse):
    """Response model of bilibili popular api"""

    data: PopularData


class WeeklyResponse(BilibiliVideoResponse):
    """Response model of bilibili weekly api"""

    data: WeeklyData


class PreciousResponse(BilibiliVideoResponse):
    data: PreciousData


class AuthorVideoResponse(BilibiliVideoResponse):
    data: AuthorVideoData


class PopularData(BilibiliVideoResponseData):
    """Data model of bilibili popular api"""

    no_more: bool
    list_data: list[PopularVideoItem] = Field([], validation_alias="list")


class WeeklyData(BilibiliVideoResponseData):
    """Data model of bilibili weekly api"""

    config: dict[str, typing.Any]
    reminder: str
    list_data: list[WeeklyVideoItem] = Field([], validation_alias="list")


class PreciousData(BilibiliVideoResponseData):
    list_data: list[PreciousVideoItem] = Field([], validation_alias="list")
    explain: str
    media_id: int
    title: str


class RankDramaData(BilibiliPlayResponseData):
    list_data: list[PlayItem] = Field([], validation_alias="list")
    note: str


class _AuthorVideoDataList(BaseModel):
    items: list[AuthorVideoItem] = Field([], validation_alias="vlist")


class AuthorVideoData(BilibiliVideoResponseData):
    list_data: _AuthorVideoDataList = Field(
        {
            "vlist": [],
        },
        validation_alias="list",
    )  # type: ignore


class VideoOwner(BaseModel):
    mid: int
    name: str
    face: str


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


class PlayStat(BaseModel):
    danmaku: int
    follow: int
    series_follow: int
    view: int


class VideoItem(BaseModel):
    aid: int
    bvid: str
    cid: int
    desc: str
    owner: VideoOwner
    pubdate: int
    short_link_v2: str
    stat: VideoStat
    tid: int
    title: str
    tname: str

    @field_serializer("owner", "stat")
    def to_string(self, value: BaseModel) -> str:
        return value.model_dump_json() if isinstance(value, BaseModel) else value


class PlayItem(BaseModel):
    rank: int
    rating: str
    stat: PlayStat
    title: str
    url: str

    @field_serializer("stat")
    def to_string(self, value: BaseModel) -> str:
        return value.model_dump_json() if isinstance(value, BaseModel) else value


class PopularVideoItem(VideoItem):
    pass


class WeeklyVideoItem(VideoItem):
    pass


class PreciousVideoItem(VideoItem):
    achievement: str


class AuthorVideoItem(BaseModel):
    title: str
    aid: int
    bvid: str
    mid: int
    comment: int
    description: str | None = None
    is_pay: int
    length: str


class VideoSource(Enum):
    POPULAR = 0
    WEEKLY = 1
    HISTORY = 2
    RANK = 3
    MUSIC = 4
    DRAMA = 5
    SEARCH = 6


class PlayInfoResponse(BaseModel):
    code: int
    message: str | None = None
    data: PlayInfoData


class PlayInfoData(BaseModel):
    accept_quality: list[int]
    accept_description: list[str]
    dash: PlayInfoDash

    @cached_property
    def quality_map(self) -> dict[int, str]:
        return dict(zip(self.accept_quality, self.accept_description))


class _PlayMediaInfo(BaseModel):
    base_url: str
    backup_url: list[str]


class PlayVideo(_PlayMediaInfo):
    quality: int = Field(..., validation_alias="id")
    codecs: str


class PlayAudio(_PlayMediaInfo):
    audio_id: int = Field(..., validation_alias="id")


class PlayInfoDash(BaseModel):
    video: conlist(PlayVideo, min_length=1)  # type: ignore
    audio: conlist(PlayAudio, min_length=1)  # type: ignore


class WbiInfo(BaseModel):
    img_url: HttpUrl
    sub_url: HttpUrl

    @cached_property
    def img_key(self) -> str:
        return self.img_url.path.split("/")[-1].split(".")[0]  # type: ignore

    @cached_property
    def sub_key(self) -> str:
        return self.sub_url.path.split("/")[-1].split(".")[0]  # type: ignore


class FeedResponse(BilibiliResponse):
    data: FeedData


class FeedData(BaseModel):
    has_more: bool
    items: list[FeedItem]
    offset: str


class FeedItemModuleStatItem(BaseModel):
    count: int


class FeedItemModuleStat(BaseModel):
    comment: FeedItemModuleStatItem
    like: FeedItemModuleStatItem
    forward: FeedItemModuleStatItem


class FeedItemModuleDynamicDesc(BaseModel):
    text: str


class FeedItemModuleDynamic(BaseModel):
    desc: FeedItemModuleDynamicDesc | None


class FeedItemModuleAuthor(BaseModel):
    jump_url: str
    pub_time: str
    pub_action: str
    name: str

    @property
    def author_action(self) -> str:
        return self.name + self.pub_action


class FeedItemModules(BaseModel):
    module_author: FeedItemModuleAuthor
    module_dynamic: FeedItemModuleDynamic
    module_stat: FeedItemModuleStat


class FeedItem(BaseModel):
    id_str: str
    modules: FeedItemModules
