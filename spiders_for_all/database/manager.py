from enum import Enum
from typing import Protocol, Type

import sqlalchemy as sa

from spiders_for_all.database import schema, session


class DDLType(Enum):
    DROP_AND_CREATE = 0
    CREATE = 1
    DROP = 2


class Manager(Protocol):
    def execute(self, s: session.SessionManager):
        pass


class DQL:
    def __init__(
        self,
        schema: Type[schema.Base] | None = None,
        raw_sql: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **params,
    ) -> None:
        self.schema = schema
        if raw_sql is not None:
            self.stmt = sa.text(raw_sql)

        else:
            self.stmt = sa.select(schema).filter_by(**params)
            if limit is not None:
                self.stmt = self.stmt.limit(limit)
            if offset is not None:
                self.stmt = self.stmt.offset(offset)

    def execute(self, s: session.SessionManager):
        with s.session() as _s:
            return _s.execute(self.stmt).fetchall()


class DDL:
    def __init__(self, *models: schema.Model, ddl_type: DDLType) -> None:
        self.models = models or None
        self.ddl_type = ddl_type

    def execute(self, s: session.SessionManager):
        with s.session():
            if self.ddl_type == DDLType.DROP_AND_CREATE:
                s.drop_all(self.models)
                s.create_all(self.models, check=False)
            elif self.ddl_type == DDLType.CREATE:
                s.create_all(self.models)
            elif self.ddl_type == DDLType.DROP:
                s.drop_all(self.models)
            else:
                raise ValueError(f"Unknown DDL type: {self.ddl_type}")
