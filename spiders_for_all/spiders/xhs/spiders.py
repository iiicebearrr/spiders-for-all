import json
import time
import typing as t
from itertools import chain
from typing import Iterable

import requests

from spiders_for_all.conf import settings
from spiders_for_all.core.spider import (
    BaseSpider,
    DbActionOnSave,
    RateLimitMixin,
    SpiderKwargs,
)
from spiders_for_all.spiders.xhs import const, db, models, patterns, schema
from spiders_for_all.utils import helper
from spiders_for_all.utils.logger import get_logger

logger = get_logger("xhs")


class BaseXhsSpider(BaseSpider):
    platform = "xhs"
    logger = logger
    session_manager = db.SessionManager


class XhsAuthorSpider(BaseXhsSpider, RateLimitMixin):
    api = const.API_AUTHOR_PAGE
    name = "author"
    alias = "作者主页"
    description = "爬取作者主页所有笔记的note id(目前暂不支持分页爬取全部, 只能爬作者首页默认显示的笔记)"

    database_model = schema.XhsAuthorNotes
    item_model = models.XhsUserPostedNote
    db_action_on_save = DbActionOnSave.UPDATE_OR_CREATE

    def __init__(
        self, uid: str, record: bool = False, **kwargs: t.Unpack[SpiderKwargs]
    ):
        super().__init__(**kwargs)
        self.uid = uid
        self.api = self.__class__.api.format(uid=uid)
        self.record = record
        self.record_note_id_list = []

        self.client.headers.update(
            {**settings.XHS_HEADERS, "x-t": str(int(time.time() * 1000))}
        )
        self.client.cookies.update(settings.XHS_COOKIES)

    def get_items_from_response(
        self,
        response: requests.Response,  # type: ignore
    ) -> t.Iterable[models.XhsUserPostedNote]:
        self.info("Searching notes info from response...")
        initial_info = patterns.RGX_FIND_INITIAL_INFO.search(response.text)
        if initial_info is None:
            self.debug(f"Raw html: {response.text}")
            raise ValueError("Initial info not found.")
        initial_info = initial_info.group(1)  # type: ignore
        try:
            json_data = helper.javascript_to_dict(initial_info)
        except json.JSONDecodeError:
            self.debug(f"Raw string: {initial_info}")
            raise ValueError("Initial info is not a valid json.")

        user_data = json_data.get("user")
        if user_data is None:
            self.debug(f"Raw json: {initial_info}")
            raise ValueError("User data not found.")

        notes = user_data.get("notes", None)
        notes_queries = user_data.get("noteQueries", [])
        if notes is None:
            self.debug(f"Raw json: {initial_info}")
            raise ValueError("Notes not found.")

        next_query = self.get_queries((models.XhsNoteQuery(**q) for q in notes_queries))

        if next_query is None:
            # No more notes
            return (
                models.XhsAuthorPageNote(**note).note_item
                for note in chain.from_iterable(notes)
            )
        else:
            # TODO: calculate x-s

            self.warning(
                "For now, we can only get the first page of notes due to the lack of x-s algorithm."
            )

            return (
                models.XhsAuthorPageNote(**note).note_item
                for note in chain.from_iterable(notes)
            )

            self.sleep((3, 6))

            image_format_collect = json_data.get("imageFormatCollect")
            if image_format_collect is not None:
                image_format_collect = [
                    formats for formats in image_format_collect.values()
                ]
                image_format_collect = ",".join(
                    list(set(sorted(chain.from_iterable(image_format_collect))))
                )

            items_from_api = self.iter_notes_by_cursor(
                query=next_query, formats=image_format_collect
            )

            return (
                self.get_note_item(note_or_item)
                for note_or_item in chain.from_iterable(
                    [
                        chain.from_iterable(notes),
                        items_from_api,
                    ]
                )
            )

    def get_queries(
        self, notes_queries: t.Iterable[models.XhsNoteQuery]
    ) -> models.XhsNoteQuery | None:
        for query in notes_queries:
            if query.cursor:
                return query

        return None

    def iter_notes_by_cursor(
        self, query: models.XhsNoteQuery, formats: str | None = None
    ) -> t.Generator[models.XhsUserPostedNote, None, None]:
        formats = formats or const.API_PARAM_IMG_FORMATS

        while query.cursor:
            self.debug(f"Fetching notes by cursor: {query.cursor}")
            self.client.headers.update({"x-t": str(int(time.time() * 1000))})
            # TODO: calculate x-s
            api = (
                const.API_AUTHOR_PAGINATION
                + "?"
                + "&".join(
                    [
                        f"{key}={value}"
                        for key, value in {
                            "num": query.num,
                            "cursor": query.cursor,
                            "user_id": query.user_id,
                            "image_formats": formats,
                        }.items()
                    ]
                )
            )
            resp = self.client.get(api)
            resp = models.XhsUserPostedResponse(**resp.json())
            resp.raise_for_status()
            if resp.data.has_more:
                self.sleep((3, 6))
            query.cursor = resp.data.cursor

            yield from resp.data.notes

    def item_to_dict(self, item: models.XhsUserPostedNote, **extra) -> dict:
        return super().item_to_dict(item, author_id=self.uid, **extra)

    def get_note_item(
        self, note_or_item: models.XhsAuthorPageNote | models.XhsUserPostedNote
    ) -> models.XhsUserPostedNote:
        if isinstance(note_or_item, models.XhsAuthorPageNote):
            return note_or_item.note_item
        return note_or_item

    def get_items(self) -> Iterable[models.XhsUserPostedNote]:
        ret: Iterable[models.XhsUserPostedNote] = super().get_items()  # type: ignore
        if not self.record:
            return ret
        for item in ret:
            yield item
            self.record_note_id_list.append(item.note_id)
