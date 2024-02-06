import json
import re
import typing as t
from itertools import chain
from typing import Iterable

import requests
from pydantic import HttpUrl

from spiders_for_all.conf import settings
from spiders_for_all.core.client import HttpClient, RequestKwargs
from spiders_for_all.core.spider import (
    BaseSpider,
    DbActionOnSave,
    PageSpider,
    RateLimitMixin,
    SleepInterval,
    SpiderKwargs,
)
from spiders_for_all.spiders.xhs import const, db, models, patterns, schema, sign
from spiders_for_all.utils import helper
from spiders_for_all.utils.logger import get_logger

logger = get_logger("xhs")


class BaseXhsSpider(BaseSpider):
    platform = "xhs"
    logger = logger
    session_manager = db.SessionManager


class BaseXhsSearchSpider(PageSpider):
    platform = "xhs"
    logger = logger
    session_manager = db.SessionManager


class XhsSignMixin:
    def sign(
        self, api: str, client: HttpClient, data: dict | str | None = None
    ) -> sign.SignData:
        """Calculate sign and update headers of client"""
        if "a1" not in client.cookies:
            raise ValueError("You must set cookies value 'a1' for this spider")
        client.debug(f"Signing with {api}, {client.cookies['a1']}")
        result = sign.get_sign(api, a1=client.cookies["a1"], data=data)
        client.headers.update(result.model_dump(by_alias=True))
        return result


class XhsAuthorSpider(BaseXhsSpider, RateLimitMixin, XhsSignMixin):
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
        self.uid = uid
        self.api = self.__class__.api.format(uid=uid)
        super().__init__(**kwargs)
        self.record = record
        self.record_note_id_list = []

        self.client.headers.update(settings.XHS_HEADERS)
        self.client.headers.update(
            {"origin": const.ORIGIN, "referer": const.ORIGIN + "/"}
        )
        self.client.cookies = settings.XHS_COOKIES

    def get_items_from_response(
        self,
        response: requests.Response,  # type: ignore
    ) -> t.Iterable[models.XhsUserPostedNote]:
        # TODO: This section may be better to be moved to `get_items`
        #       And here just return a raw response
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

        # TODO: More logs

        if next_query is None:
            # No more notes
            return (
                models.XhsAuthorPageNote(**note).note_item
                for note in chain.from_iterable(notes)
            )
        else:
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
                        [
                            models.XhsAuthorPageNote(**note).note_item
                            for note in chain.from_iterable(notes)
                        ],
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
            url = HttpUrl(
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

            self.sign(f"{url.path}?{url.query}", self.client)

            resp = self.client.get(str(url))
            resp = models.XhsUserPostedResponse(**resp.json())
            resp.raise_for_status()
            if resp.data.has_more:
                self.sleep((3, 6))
            query.cursor = resp.data.cursor
            self.info(
                f"Got {len(resp.data.notes)} notes, next cursor: {query.cursor or 'None'}"
            )

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


class XhsCommentSpider(BaseXhsSpider, RateLimitMixin, XhsSignMixin):
    api = const.API_COMMENTS
    name = "comments"
    alias = "评论"
    description = "爬取笔记的评论"

    database_model = schema.XhsNotesComments
    item_model = models.XhsNoteComment
    response_model = models.XhsNoteCommentResponse
    db_action_on_save = DbActionOnSave.UPDATE_OR_CREATE

    def __init__(
        self,
        note_id: str,
        sleep_before_next_request: SleepInterval | None = None,
        **kwargs: t.Unpack[SpiderKwargs],
    ):
        self.note_id = note_id

        super().__init__(**kwargs)

        self.client.headers.update(settings.XHS_HEADERS)
        self.client.headers.update(
            {"origin": const.ORIGIN, "referer": const.ORIGIN + "/"}
        )
        self.client.cookies = settings.XHS_COOKIES

        self.cursor: str = ""

        self.api_for_sign = str(HttpUrl(const.API_COMMENTS).path)

        self.sleep_before_next_request = sleep_before_next_request

        self.root_comment_id: str = ""

        self.total_count = 0

    def get_items_from_response(
        self, response: models.XhsNoteCommentResponse
    ) -> Iterable[models.XhsNoteComment]:
        return response.data.comments

    def get_request_args(self) -> dict:
        if self.root_comment_id:
            query = models.XhsMoreCommentQueryParam(
                note_id=self.note_id,
                cursor=self.cursor,
                top_comment_id="",
                image_formats=const.API_PARAM_IMG_FORMATS,
                root_comment_id=self.root_comment_id,
            ).model_dump()
        else:
            query = models.XhsCommentQueryParam(
                note_id=self.note_id,
                cursor=self.cursor,
                top_comment_id="",
                image_formats=const.API_PARAM_IMG_FORMATS,
            ).model_dump()

        self.sign(f"{self.api_for_sign}?{query}", self.client)

        return {
            "params": query,
        }

    def get_items(self) -> Iterable[models.XhsNoteComment]:
        has_more = True

        with self.client:
            while has_more:
                comments: list[models.XhsNoteComment] = self._get_items()  # type: ignore

                count = 0

                for comment in comments:
                    self.info(f"[Content]: {comment.content}")
                    yield comment
                    count += 1
                    if comment.sub_comments:
                        count += len(comment.sub_comments)
                        self.warning(
                            f"{comment.id} has {len(comment.sub_comments)} displayed sub comments to fetch, "
                            " and the other sub comments will be fetched after all displayed sub comments fetched."
                        )
                        yield from comment.sub_comments

                self.response: models.XhsNoteCommentResponse

                self.total_count += count
                self.info(
                    f"{count} comments fetched this time. Total fetched: {self.total_count}"
                )

                has_more = self.response.data.has_more
                self.cursor = self.response.data.cursor

                if has_more:
                    self.sleep(self.sleep_before_next_request)

    def item_to_dict(self, item: models.XhsNoteComment, **extra) -> dict:
        pictures = (
            [] if item.pictures is None else [pic.url_default for pic in item.pictures]
        )
        return {
            "comment_id": item.id,
            "content": item.content,
            "ip_location": item.ip_location,
            "like_count": item.like_count,
            "liked": item.liked,
            "note_id": self.note_id,
            "target_comment_id": item.target_comment.id
            if item.target_comment is not None
            else None,
            "pictures": ",".join(pictures),
            "sub_comment_cursor": item.sub_comment_cursor,
            "sub_comment_has_more": item.sub_comment_has_more,
            "sub_comment_count": int(item.sub_comment_count)
            if item.sub_comment_count
            else 0,
        }

    def get_sub_comments(self) -> Iterable[models.XhsNoteComment]:
        # Create a new client for sub comments fetching
        self.client = self.client.new()
        # Change api to sub api
        self.api = const.API_SUB_COMMENTS
        with self.session() as s:
            sub_comments = s.query(schema.XhsNotesComments).where(
                schema.XhsNotesComments.note_id == self.note_id,
                schema.XhsNotesComments.sub_comment_cursor.isnot(None),
                schema.XhsNotesComments.sub_comment_has_more.is_(True),
            )
            count = sub_comments.count()

            self.info(f"Found {count} sub comments need to be fetched.")

            for sub_comment in sub_comments:
                self.root_comment_id = sub_comment.comment_id
                self.cursor = sub_comment.sub_comment_cursor  # type: ignore
                self.info(f"Fetching sub comments of {self.root_comment_id}...")
                yield from self.get_items()

    def save_items(self, items: Iterable):
        super().save_items(items)
        super().save_items(self.get_sub_comments())


class XhsSearchSpider(BaseXhsSearchSpider, RateLimitMixin, XhsSignMixin):
    api = const.API_SEARCH
    name = "search"
    alias = "搜索"
    description = "主页搜索笔记"

    database_model = schema.XhsSearchNotes
    item_model = models.XhsSearchNote
    response_model = models.XhsSearchNotesResponse
    db_action_on_save = DbActionOnSave.UPDATE_OR_CREATE

    def __init__(
        self,
        keyword: str,
        total: int | None = None,
        sort: models.XhsSortType = models.XhsSortType.GENERAL,
        note_type: models.XhsSearchNoteType = models.XhsSearchNoteType.ALL,
        sleep_before_next_request: SleepInterval | None = None,
        **kwargs: t.Unpack[SpiderKwargs],
    ):
        self.keyword = keyword
        self.sort = sort
        self.note_type = note_type

        super().__init__(
            total=total, sleep_before_next_request=sleep_before_next_request, **kwargs
        )

        self.client.headers.update(settings.XHS_HEADERS)
        self.client.headers.update(
            {
                "origin": const.ORIGIN,
                "referer": const.ORIGIN + "/",
                "authority": "edith.xiaohongshu.com",
                "accept": "application/json, text/plain, */*",
                "accept-language": "en,zh-CN;q=0.9,zh;q=0.8",
                "content-type": "application/json;charset=UTF-8",
            }
        )
        self.client.cookies = settings.XHS_COOKIES

    def get_items_from_response(
        self, response: models.XhsSearchNotesResponse
    ) -> t.Iterable[models.XhsSearchNote]:
        return response.data.items or []

    def item_to_dict(self, item: models.XhsSearchNote, **extra) -> dict:
        return super().item_to_dict(
            item, keyword=self.keyword, sort=self.sort.value, **extra
        )

    def request_items(self, method: str, url: str, **kwargs: t.Unpack[RequestKwargs]):
        return super().request_items("POST", url, **kwargs)

    def get_request_args(self) -> dict:
        raw_query = {
            "image_scenes": "FD_PRV_WEBP,FD_WM_WEBP",
            "keyword": "",
            "note_type": "0",
            "page": "",
            "page_size": "20",
            "search_id": "2c7hu5b3kzoivkh848hp0",
            "sort": "general",
        }

        data = json.dumps(raw_query, separators=(",", ":"))

        data = re.sub(r'"keyword":".*?"', f'"keyword":"{self.keyword}"', data)
        data = re.sub(r'"page":".*?"', f'"page":"{self.page_number}"', data)
        data = re.sub(r'"sort":".*?"', f'"sort":"{self.sort.value}"', data)
        data = re.sub(
            r'"note_type":".*?"', f'"note_type":"{self.note_type.value}"', data
        )

        # TODO: Remove hard code
        self.sign("/api/sns/web/v1/search/notes", self.client, data=data)

        return {
            "data": data.encode("utf-8"),
        }

    def get_items(self) -> t.Iterable[models.XhsSearchNote]:
        # Note: This return_items may not equal to self.page_size
        #       So we should use `has_more` to control the loop

        has_more = True
        count = 0
        stop = False

        with self.client:
            while has_more:
                notes: list[models.XhsSearchNote] = self._get_items()  # type: ignore

                for note in notes:
                    yield note
                    count += 1
                    self.info(f"Note id: {note.note_id}. {count}/{self.total}")

                    if self.total is not None and count >= self.total:
                        stop = True
                        break

                self.page_number += 1

                if stop:
                    break

                self.response: models.XhsSearchNotesResponse

                has_more = self.response.data.has_more

                if has_more:
                    self.sleep(self.sleep_before_next_request)
