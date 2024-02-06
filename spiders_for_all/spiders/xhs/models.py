from __future__ import annotations

import typing as t
from enum import Enum

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from spiders_for_all.core.response import Response


class XhsResponse(Response):
    code: int
    data: t.Any
    message: str | None = None
    success: bool

    def raise_for_status(self):
        if not self.success:
            raise ValueError(self.message)


class XhsUserPostedNote(BaseModel):
    note_id: str = Field(..., validation_alias=AliasChoices("note_id", "noteId"))
    note_title: str = Field(
        ..., validation_alias=AliasChoices("display_title", "displayTitle")
    )
    note_type: str = Field(..., validation_alias="type")


class XhsUserPostedResponseData(BaseModel):
    cursor: str
    has_more: bool
    notes: list[XhsUserPostedNote]


class XhsUserShort(BaseModel):
    user_id: str
    nickname: str


class XhsTargetComment(BaseModel):
    user_info: XhsUserShort
    id: str


class XhsNotePicture(BaseModel):
    url_pre: str
    url_default: str


class XhsNoteComment(BaseModel):
    user_info: XhsUserShort
    at_users: list[XhsUserShort]
    content: str
    id: str
    ip_location: str | None = None
    like_count: int
    liked: bool
    note_id: str
    sub_comments: list[XhsNoteComment] | None = None
    sub_comment_cursor: str | None = None
    sub_comment_has_more: bool | None = None
    sub_comment_count: str | None = None
    pictures: list[XhsNotePicture] | None = None
    target_comment: XhsTargetComment | None = None


class XhsNoteCommentResponseData(BaseModel):
    cursor: str = ""
    has_more: bool
    time: int
    user_id: str
    comments: list[XhsNoteComment]


class XhsUserPostedResponse(XhsResponse):
    data: XhsUserPostedResponseData


class XhsNoteCommentResponse(XhsResponse):
    data: XhsNoteCommentResponseData


class XhsNoteType(Enum):
    NORMAL = "normal"
    VIDEO = "video"


class XhsNoteTag(BaseModel):
    tag_id: str = Field(..., validation_alias="id")
    name: str
    tag_type: str = Field(..., validation_alias="type")


class XhsNoteImage(BaseModel):
    url_default: str = Field(..., validation_alias="urlDefault")


class XhsVideoItem(BaseModel):
    master_url: str = Field(..., validation_alias="masterUrl")
    audio_codec: str = Field(..., validation_alias="audioCodec")
    audio_duration: int = Field(..., validation_alias="audioDuration")
    size: int
    video_duration: int = Field(..., validation_alias="videoDuration")
    video_codec: str = Field(..., validation_alias="videoCodec")
    quality_type: str = Field(..., validation_alias="qualityType")


class XhsVideoMedia(BaseModel):
    stream: dict[str, list[XhsVideoItem]]

    def iter_video_item(self) -> t.Generator[XhsVideoItem, None, None]:
        for _, video_items in self.stream.items():
            yield from video_items


class XhsVideo(BaseModel):
    media: XhsVideoMedia


class XhsNote(BaseModel):
    tag_list: list[XhsNoteTag] = Field(..., validation_alias="tagList")
    image_list: list[XhsNoteImage] = Field(..., validation_alias="imageList")
    note_type: XhsNoteType = Field(XhsNoteType.NORMAL, validation_alias="type")
    title: str
    desc: str | None = None
    video: XhsVideo | None = None


class XhsAuthorPageNote(BaseModel):
    id: str = Field(..., description="Note id, equal to note_card.note_id")
    note_item: XhsUserPostedNote = Field(..., validation_alias="noteCard")


class XhsNoteQuery(BaseModel):
    num: int
    cursor: str = ""
    user_id: str = Field(..., validation_alias="userId")
    has_more: bool = Field(..., validation_alias="hasMore")


class XhsCommentQueryParam(BaseModel):
    note_id: str
    cursor: str
    top_comment_id: str
    image_formats: str


class XhsMoreCommentQueryParam(XhsCommentQueryParam):
    root_comment_id: str
    num: int = 10


class XhsSearchNoteType(Enum):
    ALL = 0
    NORMAL = 2
    VIDEO = 1


class XhsSortType(Enum):
    GENERAL = "general"
    TIME_DESCENDING = "time_descending"
    POPULARITY_DESCENDING = "popularity_descending"


class XhsSearchNoteQuery(BaseModel):
    image_formats: list[str] = ["jpg", "webp", "avif"]
    keyword: str
    note_type: XhsSearchNoteType = XhsSearchNoteType.NORMAL
    page: str
    page_size: str
    search_id: str
    sort: XhsSortType = XhsSortType.GENERAL

    model_config = ConfigDict(use_enum_values=True)


class XhsSearchNote(BaseModel):
    # id is enough.
    note_id: str = Field(..., validation_alias="id")


class XhsSearchNotesResponseData(BaseModel):
    has_more: bool
    items: list[XhsSearchNote] | None = None


class XhsSearchNotesResponse(XhsResponse):
    data: XhsSearchNotesResponseData
