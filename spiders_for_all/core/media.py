from enum import Enum, auto

from pydantic import HttpUrl


class MediaType(Enum):
    VIDEO = auto()
    AUDIO = auto()
    IMAGE = auto()
    TEXT = auto()


class Media:
    media_type: MediaType
    suffix: str

    def __init__(
        self,
        *args,
        complete_url: str | None = None,
        base_url: str | None = None,
        url_id: str | None = None,
        name: str | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.complete_url = complete_url
        self.base_url = base_url
        self.url_id = url_id
        self.name = name or self.media_type

        self.url = self.get_url()

    def get_url(self) -> HttpUrl:
        if self.complete_url:
            return HttpUrl(self.complete_url)
        if self.base_url and self.url_id:
            return HttpUrl(self.base_url.rstrip("/") + "/" + self.url_id.lstrip("/"))
        raise ValueError("Media url is not set correctly.")


class Video(Media):
    media_type = MediaType.VIDEO
    suffix = "mp4"


class Audio(Media):
    media_type = MediaType.AUDIO
    suffix = "mp3"


class Image(Media):
    media_type = MediaType.IMAGE
    suffix = "img"


class Text(Media):
    media_type = MediaType.TEXT
    suffix = "txt"


class JPG(Image):
    suffix = "jpg"


class PNG(Image):
    suffix = "png"


class GIF(Image):
    suffix = "gif"


class WEBP(Image):
    suffix = "webp"


class BMP(Image):
    suffix = "bmp"


class TIFF(Image):
    suffix = "tiff"


class ICO(Image):
    suffix = "ico"


class HTML(Text):
    suffix = "html"


class JSON(Text):
    suffix = "json"
