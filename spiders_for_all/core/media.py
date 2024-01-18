from enum import Enum, auto
from functools import cached_property

from pydantic import HttpUrl


class MediaType(Enum):
    VIDEO = auto()
    AUDIO = auto()
    IMAGE = auto()
    TEXT = auto()


class Media:
    media_type: MediaType
    suffix: str
    description: str = ""

    def __init__(
        self,
        *args,
        base_url: str,
        backup_url: list[str] | None = None,
        name: str | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.base_url = base_url
        self.backup_url = backup_url or []
        self.name = name or "NAME NOT SET"

    @cached_property
    def url(self) -> str:
        return str(self.get_url(self.base_url))

    @cached_property
    def urls(self) -> list[str]:
        if not self.backup_url:
            return [self.url]
        _urls = [self.base_url]
        _urls.extend(self.backup_url)
        return [str(self.get_url(url)) for url in _urls]

    def get_url(self, url: str) -> HttpUrl:
        return HttpUrl(url)

    def __str__(self) -> str:
        if not self.description:
            return f"<{self.name}>"
        return f"<{self.name} {self.description}>"


class Mp4(Media):
    media_type = MediaType.VIDEO
    suffix = ".mp4"


class Mp3(Media):
    media_type = MediaType.AUDIO
    suffix = ".mp3"


class Image(Media):
    media_type = MediaType.IMAGE
    suffix = ".img"


class Text(Media):
    media_type = MediaType.TEXT
    suffix = ".txt"


class JPG(Image):
    suffix = ".jpg"


class PNG(Image):
    suffix = ".png"


class GIF(Image):
    suffix = ".gif"


class WEBP(Image):
    suffix = ".webp"


class BMP(Image):
    suffix = ".bmp"


class TIFF(Image):
    suffix = ".tiff"


class ICO(Image):
    suffix = ".ico"


class HTML(Text):
    suffix = ".html"


class JSON(Text):
    suffix = ".json"
