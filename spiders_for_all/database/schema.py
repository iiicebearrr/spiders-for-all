from datetime import datetime
from typing import Sequence, Type, TypeAlias

import sqlalchemy as sa
from sqlalchemy import orm


class Base(orm.DeclarativeBase):
    pass


Model: TypeAlias = Type[orm.DeclarativeBase]
Models: TypeAlias = Sequence[Model]


class BaseTable(Base):
    __abstract__ = True

    id: orm.Mapped[int] = orm.mapped_column(
        primary_key=True, comment="auto increment id"
    )

    create_at: orm.Mapped[datetime] = orm.mapped_column(
        default=datetime.now, comment="create time of a video"
    )

    update_at: orm.Mapped[datetime] = orm.mapped_column(
        default=datetime.now, comment="update time of a video", onupdate=datetime.now
    )

    def tuple(self):
        return tuple(
            [
                getattr(self, column.key)
                for column in sa.inspect(self).mapper.column_attrs
            ]
        )
