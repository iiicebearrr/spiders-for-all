import typing as t
from enum import Enum

from pydantic import AliasChoices, BaseModel, Field

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


class XhsUserPostedResponse(XhsResponse):
    data: XhsUserPostedResponseData


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
