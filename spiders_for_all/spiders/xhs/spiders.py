import json
from itertools import chain
from typing import Iterable, Unpack

from requests.models import Response as Response

from spiders_for_all.core.spider import BaseSpider, DbActionOnSave, SpiderKwargs
from spiders_for_all.spiders.xhs import db, models, patterns, schema
from spiders_for_all.utils import helper
from spiders_for_all.utils.logger import get_logger

logger = get_logger("xhs")


class BaseXhsSpider(BaseSpider):
    platform = "xhs"
    logger = logger
    session_manager = db.SessionManager


class XhsAuthorSpider(BaseXhsSpider):
    api = "https://www.xiaohongshu.com/user/profile/{uid}"
    name = "author"
    alias = "作者主页"

    database_model = schema.XhsAuthorNotes
    item_model = models.XhsAuthorPageNoteItem
    db_action_on_save = DbActionOnSave.UPDATE_OR_CREATE

    def __init__(self, uid: str, **kwargs: Unpack[SpiderKwargs]):
        super().__init__(**kwargs)
        self.uid = uid
        self.api = self.__class__.api.format(uid=uid)

    def get_items_from_response(
        self, response: Response
    ) -> Iterable[models.XhsAuthorPageNoteItem]:
        initial_info = patterns.RGX_FIND_INITIAL_INFO.search(response.text)
        if initial_info is None:
            self.debug(f"Raw html: {response.text}")
            raise ValueError("Initial info not found.")
        initial_info = initial_info.group(1)
        try:
            json_data = helper.javascript_to_dict(initial_info)
        except json.JSONDecodeError:
            self.debug(f"Raw string: {initial_info}")
            raise ValueError("Initial info is not a valid json.")
        notes = json_data.get("user", {}).get("notes", None)
        if notes is None:
            self.debug(f"Raw json: {initial_info}")
            raise ValueError("Notes not found.")
        return (
            models.XhsAuthorPageNote(**note).note_item
            for note in chain.from_iterable(notes)
        )

    def item_to_dict(self, item: models.XhsAuthorPageNoteItem, **extra) -> dict:
        return super().item_to_dict(item, author_id=self.uid, **extra)


if __name__ == "__main__":
    spider = XhsAuthorSpider(uid="5a006564e8ac2b01d7a1e082")
    spider.run()
