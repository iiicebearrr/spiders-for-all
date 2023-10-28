from __future__ import annotations
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_serializer


class BilibiliResponse(BaseModel):
    code: int
    data: BilibiliResponseData
    message: str | None
    ttl: int


class BilibiliResponseData(BaseModel):
    list_data: list[PydanticBilibiliPopularVideo] = Field([], validation_alias="list")
    no_more: bool


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


class PydanticBilibiliPopularVideo(BaseModel):
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
        return value.model_dump_json()
