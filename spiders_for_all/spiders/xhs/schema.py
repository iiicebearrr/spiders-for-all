import typing as t

from pydantic import HttpUrl
from sqlalchemy import orm
from sqlalchemy.ext.hybrid import hybrid_property

from spiders_for_all.database.schema import BaseTable


class XhsAuthorNotesBase(BaseTable):
    __abstract__ = True

    note_id: orm.Mapped[str] = orm.mapped_column(unique=True)


class XhsAuthorNotes(XhsAuthorNotesBase):
    __tablename__ = "t_xhs_author_notes"
    __doc__ = "Main page of author's notes"

    author_id: orm.Mapped[str]
    note_title: orm.Mapped[str]
    note_type: orm.Mapped[str]


class XhsSearchNotes(XhsAuthorNotesBase):
    __tablename__ = "t_xhs_search_notes"

    keyword: orm.Mapped[str]


class XhsNotesContent(XhsAuthorNotesBase):
    __tablename__ = "t_xhs_notes_content"
    __doc__ = "Notes content"

    description: orm.Mapped[str]
    tags_list: orm.Mapped[t.Optional[str]]


class XhsNotesComments(BaseTable):
    __tablename__ = "t_xhs_notes_comments"
    __doc__ = "Comments of notes"

    comment_id: orm.Mapped[str] = orm.mapped_column(unique=True)
    note_id: orm.Mapped[str]
    content: orm.Mapped[str]
    ip_location: orm.Mapped[str]
    like_count: orm.Mapped[int]
    liked: orm.Mapped[bool]
    target_comment_id: orm.Mapped[t.Optional[str]] = orm.mapped_column(
        comment="target comment id",
        nullable=True,
    )
    pictures: orm.Mapped[t.Optional[str]] = orm.mapped_column(
        comment="pictures of a comment",
        nullable=True,
    )
    sub_comment_cursor: orm.Mapped[t.Optional[str]] = orm.mapped_column(
        comment="sub comment cursor",
        nullable=True,
    )
    sub_comment_has_more: orm.Mapped[t.Optional[bool]] = orm.mapped_column(
        comment="sub comment has more",
        nullable=True,
    )
    sub_comment_count: orm.Mapped[t.Optional[int]] = orm.mapped_column(
        comment="sub comment count",
        nullable=True,
    )

    @hybrid_property
    def pictures_list(self) -> list[HttpUrl]:
        if self.pictures is None:
            return []
        return [HttpUrl(url) for url in self.pictures.split(",")]
