from enum import Enum, auto

import sqlalchemy as sa
from rich import print
from sqlalchemy import orm

from spiders_for_all.conf import settings
from spiders_for_all.database import schema
from spiders_for_all.utils import helper


class DatabaseOperationType(Enum):
    DROP_IF_EXIST = auto()  # Drop all tables if exists
    CREATE_IF_NOT_EXIST = auto()  # Create all tables if not exists
    CREATE = auto()  # Create all tables
    DROP = auto()  # Drop all tables
    DROP_AND_CREATE = auto()  # Drop all tables and create them again


class SessionManager:
    def __init__(self, db_filename: str) -> None:
        self.filename = helper.correct_filename(db_filename)

        self.filepath = settings.DB_DIR / db_filename

        if self.filepath.suffix != ".db":
            self.filepath = self.filepath.with_suffix(".db")

        self.engine = sa.engine.create_engine(
            f"sqlite:///{str(self.filepath)}", echo=settings.DEBUG
        )

        self.session = orm.sessionmaker(bind=self.engine)

    def init_db(self, operation: DatabaseOperationType):
        if operation == DatabaseOperationType.DROP_IF_EXIST:
            self.drop_all()
        elif operation == DatabaseOperationType.CREATE_IF_NOT_EXIST:
            self.create_all()
        elif operation == DatabaseOperationType.CREATE:
            self.create_all(check=False)
        elif operation == DatabaseOperationType.DROP:
            self.drop_all(check=False)
        elif operation == DatabaseOperationType.DROP_AND_CREATE:
            self.drop_all()
            self.create_all(check=False)
        else:
            raise ValueError(f"Unknown database operation: {operation}")

    def drop_all(self, models: schema.Models | None = None, check: bool = True):
        print(f"Drop database: {self.filepath}...")
        schema.Base.metadata.drop_all(
            self.engine,
            checkfirst=check,
            tables=[model.__table__ for model in models],  # type: ignore
        )

    def create_all(self, models: schema.Models | None = None, check: bool = True):
        if self.filepath.exists():
            print(f"Using database: {self.filepath}")
        else:
            print(f"Create database: {self.filepath}...")
        schema.Base.metadata.create_all(
            self.engine,
            checkfirst=check,
            tables=[model.__table__ for model in models],  # type: ignore
        )
