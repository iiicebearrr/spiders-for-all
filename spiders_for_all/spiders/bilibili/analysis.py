import json
from enum import Enum, auto
from functools import cached_property
from typing import Type, TypeAlias

from rich import print
from rich import table as rich_table
from sqlalchemy import Row

from spiders_for_all.spiders.bilibili import db, schema

ViewCount: TypeAlias = int
SortData: TypeAlias = tuple[int, tuple[ViewCount, Row]]  # row_id, (view_count, row)
VideoOrPlay: TypeAlias = schema.BaseBilibiliVideos | schema.BaseBilibiliPlay
VideoOrPlayClass: TypeAlias = Type[VideoOrPlay]
TableModelClass: TypeAlias = Type[schema.BaseTable]

N: int = 10


class ShowType(Enum):
    COMMON = auto()
    VIDEO_OR_PLAY = auto()


class Analysis:
    def __init__(self, model: TableModelClass, n: int = N) -> None:
        """_summary_

        Args:
            model (Model): model to analysis
            n (int, optional): N rows to analysis. Defaults to 10.

        Raises:
            TypeError: _description_
        """

        self.model = model
        self.n = n
        if not issubclass(model, (schema.BaseBilibiliVideos, schema.BaseBilibiliPlay)):
            self.table = self.get_table(self.get_model_columns(model))
            self.show_type = ShowType.COMMON
        else:
            self.table = rich_table.Table(
                "rank",
                "title",
                "view",
                "link",
                title=f"Top {n} videos",
                show_header=True,
                header_style="bold magenta",
                show_lines=True,
            )
            self.show_type = ShowType.VIDEO_OR_PLAY

    @staticmethod
    def get_model_columns(model: TableModelClass) -> list[str]:
        return model.__table__.columns.keys()

    def get_table(self, columns: list[str]) -> rich_table.Table:
        return rich_table.Table(
            *columns,
            title=f"Top {self.n} videos",
            show_header=True,
            header_style="bold magenta",
            show_lines=True,
        )

    def _key(self, videos_tuple: SortData):
        return videos_tuple[1][0]

    @cached_property
    def url_field(self) -> str:
        if issubclass(self.model, schema.BaseBilibiliVideos):
            return "short_link_v2"
        return "url"

    def add_videos_or_plays_row(self, model: VideoOrPlayClass):
        with db.Session() as s:
            videos_data: dict[int, tuple[ViewCount, Row]] = {
                item.id: (json.loads(item.stat)["view"], item)
                for item in s.query(
                    model.id,
                    model.stat,
                    model.title,
                    getattr(self.model, self.url_field),
                )  # type: ignore
            }
            videos_data = dict(sorted(videos_data.items(), key=self._key))
            count = 0
            for i, (_, item_tuple) in enumerate(videos_data.items()):
                view_count, row = item_tuple
                if count >= self.n:
                    break

                self.table.add_row(
                    str(i + 1), row.title, str(view_count), getattr(row, self.url_field)
                )

                count += 1

    def add_common_row(self, model: TableModelClass):
        with db.Session() as s:
            for i, row in enumerate(s.query(model)):
                if i >= self.n:
                    break
                self.table.add_row(*[str(value) for value in row.tuple()])  # type: ignore

    def show(self):
        if self.show_type == ShowType.VIDEO_OR_PLAY:
            self.add_videos_or_plays_row(self.model)  # type: ignore
        else:
            self.add_common_row(self.model)

        print(self.table)
