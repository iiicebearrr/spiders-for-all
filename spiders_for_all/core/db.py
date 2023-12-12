import sqlalchemy as sa
from spiders_for_all.conf import settings
from spiders_for_all.utils import helper
from sqlalchemy import orm
from datetime import datetime
from rich import print
from enum import Enum, auto
from typing import Sequence, TypeAlias, Type


class Base(orm.DeclarativeBase):
    pass


Models: TypeAlias = Sequence[Type[Base]]


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


class DatabaseOperationType(Enum):
    DROP_IF_EXIST = auto()  # Drop all tables if exists
    CREATE_IF_NOT_EXIST = auto()  # Create all tables if not exists
    CREATE = auto()  # Create all tables
    DROP = auto()  # Drop all tables
    DROP_AND_CREATE = auto()  # Drop all tables and create them again


class SessionMaker:
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

    def drop_all(self, models: Models | None = None, check: bool = True):
        print(f"Drop database: {self.filepath}...")
        Base.metadata.drop_all(
            self.engine,
            checkfirst=check,
            tables=[model.__table__ for model in models],  # type: ignore
        )

    def create_all(self, models: Models | None = None, check: bool = True):
        print(f"Create database: {self.filepath}...")
        Base.metadata.create_all(
            self.engine,
            checkfirst=check,
            tables=[model.__table__ for model in models],  # type: ignore
        )
