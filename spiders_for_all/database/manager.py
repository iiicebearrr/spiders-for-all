from enum import Enum
from typing import Protocol

from spiders_for_all.database import schema, session


class DDLType(Enum):
    DROP_AND_CREATE = 0
    CREATE = 1
    DROP = 2


class Manager(Protocol):
    def execute(self, s: session.SessionManager):
        pass


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
