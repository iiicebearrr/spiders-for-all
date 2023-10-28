import sqlalchemy as sa
from sqlalchemy import orm
from datetime import datetime
from bilibili import models
from functools import cached_property, wraps

engine = sa.engine.create_engine("sqlite:///bilibili.db", echo=True)

Session = sa.orm.sessionmaker(bind=engine)


class Base(orm.DeclarativeBase):
    pass


class BaseBilibiliVideos(Base):
    __abstract__ = True

    id: orm.Mapped[int] = orm.mapped_column(
        primary_key=True, comment="auto increment id"
    )
    aid: orm.Mapped[int] = orm.mapped_column(unique=True, comment="avid of a video")
    bvid: orm.Mapped[str] = orm.mapped_column(unique=True, comment="bvid of a video")
    cid: orm.Mapped[int] = orm.mapped_column(comment="cid")
    copyright: orm.Mapped[int] = orm.mapped_column(comment="copyright")
    desc: orm.Mapped[str] = orm.mapped_column(comment="description of a video")
    duration: orm.Mapped[int] = orm.mapped_column(comment="duration of a video")
    dynamic: orm.Mapped[str] = orm.mapped_column(comment="dynamic of a video")
    enable_vt: orm.Mapped[bool] = orm.mapped_column(comment="enable_vt of a video")
    first_frame: orm.Mapped[str] = orm.mapped_column(
        comment="first_frame of a video", nullable=True
    )
    is_ogv: orm.Mapped[int] = orm.mapped_column(comment="is_ogv of a video")
    mission_id: orm.Mapped[int] = orm.mapped_column(
        comment="mission_id of a video", nullable=True
    )
    owner: orm.Mapped[int] = orm.mapped_column(comment="owner info of a video")
    pic: orm.Mapped[str] = orm.mapped_column(comment="pic of a video")
    pub_location: orm.Mapped[str] = orm.mapped_column(comment="pub_location of a video")
    pubdate: orm.Mapped[int] = orm.mapped_column(comment="pubdate of a video")
    rcmd_reason: orm.Mapped[str] = orm.mapped_column(
        comment="recommended reason of a video"
    )
    season_type: orm.Mapped[int] = orm.mapped_column(comment="season_type of a video")
    short_link_v2: orm.Mapped[str] = orm.mapped_column(
        comment="short_link_v2 of a video"
    )
    stat: orm.Mapped[str] = orm.mapped_column(comment="stat of a video")
    state: orm.Mapped[int] = orm.mapped_column(comment="state of a video")
    tid: orm.Mapped[int] = orm.mapped_column(comment="tid of a video")
    title: orm.Mapped[str] = orm.mapped_column(comment="title of a video")
    tname: orm.Mapped[str] = orm.mapped_column(comment="tag name of a video")
    videos: orm.Mapped[int] = orm.mapped_column(comment="videos of a video")

    create_at: orm.Mapped[datetime] = orm.mapped_column(
        default=datetime.now, comment="create time of a video"
    )

    update_at: orm.Mapped[datetime] = orm.mapped_column(
        default=datetime.now, comment="update time of a video", onupdate=datetime.now
    )

    @cached_property
    def owner_info(self) -> models.VideoOwner:
        return models.VideoOwner(**self.owner)

    @cached_property
    def stat_info(self) -> models.VideoStat:
        return models.VideoStat(**self.stat)

    @cached_property
    def rcmd_reason_info(self) -> models.RecommendReason:
        return models.RecommendReason(**self.rcmd_reason)


class BilibiliPopularVideos(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_popular_videos"
    __doc__ = "bilibili popular videos information"


class BilibiliWeeklyVideos(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_weekly_videos"
    __doc__ = "bilibili weekly videos information"

    aid: orm.Mapped[int] = orm.mapped_column(comment="avid of a video")
    bvid: orm.Mapped[str] = orm.mapped_column(comment="bvid of a video")
    week: orm.Mapped[int] = orm.mapped_column(comment="Which week of a video")
    rcmd_reason: orm.Mapped[str]


def init_db():
    """init database"""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def session(func):
    """
    session decorator

    Usage:

    from bilibili import db

    @db.session
    def func():
        ...

    """

    @wraps(func)
    def inner(*args, **kwargs):
        # TODO: session decorator
        return func(*args, **kwargs)

    return inner


if __name__ == "__main__":
    init_db()
