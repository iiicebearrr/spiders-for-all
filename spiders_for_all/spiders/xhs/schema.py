import typing as t

from sqlalchemy import orm

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


class XhsNotesContent(XhsAuthorNotesBase):
    __tablename__ = "t_xhs_notes_content"
    __doc__ = "Notes content"

    description: orm.Mapped[str]
    tags_list: orm.Mapped[t.Optional[str]]
