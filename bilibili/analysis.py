import json
import typing
from functools import cached_property

from rich import print
from rich import table as rich_table
from sqlalchemy import Row

from bilibili import db

type SortData = tuple[int, tuple[int, Row]]  # row_id, (view_count, row)
type Model = typing.Type[db.BaseBilibiliVideos | db.BaseBilibiliPlay]


class Analysis:
    def __init__(self, model: Model, n: int = 10) -> None:
        if not issubclass(model, (db.BaseBilibiliVideos, db.BaseBilibiliPlay)):
            raise TypeError(f"{model} is not a valid video model")

        self.model = model
        self.n = n
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

    def _key(self, videos_tuple: SortData):
        return videos_tuple[1][0]

    @cached_property
    def url_field(self) -> str:
        if issubclass(self.model, db.BaseBilibiliVideos):
            return "short_link_v2"
        return "url"

    def show(self):
        with db.Session() as s:
            videos_data: dict[int, tuple[int, Row]] = {
                item.id: (json.loads(item.stat)["view"], item)
                for item in s.query(
                    self.model.id,
                    self.model.stat,
                    self.model.title,
                    getattr(self.model, self.url_field),
                )
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

        print(self.table)


if __name__ == "__main__":
    a = Analysis(db.BilibiliRankCnCartoon)

    a.show()
