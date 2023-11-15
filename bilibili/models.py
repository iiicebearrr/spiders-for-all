from __future__ import annotations

import typing
from enum import Enum
from functools import cached_property

from pydantic import BaseModel, Field, field_serializer, conlist


class BilibiliResponse(BaseModel):
    code: int
    data: typing.Any
    message: str | None = None


class BilibiliVideoResponse(BilibiliResponse):
    """Base response model of bilibili api"""

    data: BilibiliVideoResponseData


class BilibiliPlayResponse(BilibiliResponse):
    data: BilibiliPlayResponseData


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


class BilibiliVideoResponseData(BaseModel):
    """Base data model of bilibili api"""

    list_data: typing.Sequence[VideoModel] = Field([], validation_alias="list")


class BilibiliPlayResponseData(BaseModel):
    list_data: typing.Sequence[PlayModel] = Field([], validation_alias="list")


class PopularData(BilibiliVideoResponseData):
    """Data model of bilibili popular api"""

    no_more: bool
    list_data: list[PopularVideoModel] = Field([], validation_alias="list")


class WeeklyData(BilibiliVideoResponseData):
    """Data model of bilibili weekly api"""

    config: dict[str, typing.Any]
    reminder: str
    list_data: list[WeeklyVideoModel] = Field([], validation_alias="list")


class PreciousData(BilibiliVideoResponseData):
    list_data: list[PreciousVideoModel] = Field([], validation_alias="list")
    explain: str
    media_id: int
    title: str


class RankDramaData(BilibiliPlayResponseData):
    list_data: list[PlayModel] = Field([], validation_alias="list")
    note: str


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


class VideoModel(BaseModel):
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


class PlayModel(BaseModel):
    rank: int
    rating: str
    stat: PlayStat
    title: str
    url: str

    @field_serializer("stat")
    def to_string(self, value: BaseModel) -> str:
        return value.model_dump_json() if isinstance(value, BaseModel) else value


class PopularVideoModel(VideoModel):
    pass


class WeeklyVideoModel(VideoModel):
    pass


class PreciousVideoModel(VideoModel):
    achievement: str


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
