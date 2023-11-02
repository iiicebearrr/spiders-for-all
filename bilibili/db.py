from datetime import datetime
from functools import cached_property

import sqlalchemy as sa
from sqlalchemy import orm

from bilibili import models
from conf import settings

engine = sa.engine.create_engine("sqlite:///bilibili.db", echo=settings.DEBUG)

Session = sa.orm.sessionmaker(bind=engine)


class Base(orm.DeclarativeBase):
    pass


class BaseBilibiliVideos(Base):
    __abstract__ = True

    id: orm.Mapped[int] = orm.mapped_column(
        primary_key=True, comment="auto increment id"
    )
    title: orm.Mapped[str] = orm.mapped_column(comment="title of a video")
    tname: orm.Mapped[str] = orm.mapped_column(comment="tag name of a video")

    aid: orm.Mapped[int] = orm.mapped_column(unique=True, comment="avid of a video")
    bvid: orm.Mapped[str] = orm.mapped_column(unique=True, comment="bvid of a video")
    cid: orm.Mapped[int] = orm.mapped_column(comment="cid")
    desc: orm.Mapped[str] = orm.mapped_column(comment="description of a video")
    owner: orm.Mapped[str] = orm.mapped_column(comment="owner info of a video")
    pubdate: orm.Mapped[int] = orm.mapped_column(comment="pubdate of a video")
    short_link_v2: orm.Mapped[str] = orm.mapped_column(
        comment="short_link_v2 of a video"
    )
    stat: orm.Mapped[str] = orm.mapped_column(comment="stat of a video")
    tid: orm.Mapped[int] = orm.mapped_column(comment="tid of a video")

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


class BaseBilibiliPlay(Base):
    __abstract__ = True

    id: orm.Mapped[int] = orm.mapped_column(
        comment="auto increment id", primary_key=True
    )
    rank: orm.Mapped[int] = orm.mapped_column(comment="rank of a video")
    rating: orm.Mapped[str] = orm.mapped_column(comment="rating of a video")
    stat: orm.Mapped[str] = orm.mapped_column(comment="stat of a video")
    title: orm.Mapped[str] = orm.mapped_column(comment="title of a video")
    url: orm.Mapped[str] = orm.mapped_column(comment="url of a video")

    create_at: orm.Mapped[datetime] = orm.mapped_column(
        default=datetime.now, comment="create time of a video"
    )

    update_at: orm.Mapped[datetime] = orm.mapped_column(
        default=datetime.now, comment="update time of a video", onupdate=datetime.now
    )


class BilibiliPopularVideos(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_popular_videos"
    __doc__ = "bilibili popular videos information"


class BilibiliWeeklyVideos(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_weekly_videos"
    __doc__ = "bilibili weekly videos information"

    aid: orm.Mapped[int] = orm.mapped_column(comment="avid of a video")
    bvid: orm.Mapped[str] = orm.mapped_column(comment="bvid of a video")
    week: orm.Mapped[int] = orm.mapped_column(comment="Which week of a video")


class BilibiliPreciousVideos(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_precious_videos"
    __doc__ = "bilibili precious videos information"

    achievement: orm.Mapped[str]
    bvid: orm.Mapped[str] = orm.mapped_column(comment="bvid of a video")
    aid: orm.Mapped[int] = orm.mapped_column(comment="avid of a video")


class BilibiliRankDrama(BaseBilibiliPlay):
    __tablename__ = "t_bilibili_rank_drama"
    __doc__ = "bilibili rank drama information"


class BilibiliRankAll(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_all"
    __doc__ = "bilibili rank all information"


class BilibiliRankCnCartoon(BaseBilibiliPlay):
    __tablename__ = "t_bilibili_rank_cn_cartoon"
    __doc__ = "bilibili rank cn cartoon information"


class BilibiliRankCnRelated(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_cn_related"
    __doc__ = "bilibili rank cn related information"


class BilibiliRankDocumentary(BaseBilibiliPlay):
    __tablename__ = "t_bilibili_rank_documentary"
    __doc__ = "bilibili rank documentary information"


class BilibiliRankCartoon(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_cartoon"
    __doc__ = "bilibili rank cartoon information"


class BilibiliRankMusic(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_music"
    __doc__ = "bilibili rank music information"


class BilibiliRankDance(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_dance"
    __doc__ = "bilibili rank dance information"


class BilibiliRankGame(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_game"
    __doc__ = "bilibili rank game information"


class BilibiliRankTech(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_tech"
    __doc__ = "bilibili rank tech information"


class BilibiliRankKnowledge(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_knowledge"
    __doc__ = "bilibili rank knowledge information"


class BilibiliRankSport(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_sport"
    __doc__ = "bilibili rank sport information"


class BilibiliRankCar(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_car"
    __doc__ = "bilibili rank car information"


class BilibiliRankLife(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_life"
    __doc__ = "bilibili rank life information"


class BilibiliRankFood(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_food"
    __doc__ = "bilibili rank food information"


class BilibiliRankAnimal(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_animal"
    __doc__ = "bilibili rank animal information"


class BilibiliRankAuto(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_auto"
    __doc__ = "bilibili rank auto information"


class BilibiliRankFashion(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_fashion"
    __doc__ = "bilibili rank fashion information"


class BilibiliRankEnt(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_ent"
    __doc__ = "bilibili rank ent information"


class BilibiliRankFilm(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_film"
    __doc__ = "bilibili rank film information"


class BilibiliRankMovie(BaseBilibiliPlay):
    __tablename__ = "t_bilibili_rank_movie"
    __doc__ = "bilibili rank movie information"


class BilibiliRankTv(BaseBilibiliPlay):
    __tablename__ = "t_bilibili_rank_tv"
    __doc__ = "bilibili rank tv information"


class BilibiliRankVariety(BaseBilibiliPlay):
    __tablename__ = "t_bilibili_rank_variety"
    __doc__ = "bilibili rank variety information"


class BilibiliRankOrigin(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_origin"
    __doc__ = "bilibili rank origin information"


class BilibiliRankNew(BaseBilibiliVideos):
    __tablename__ = "t_bilibili_rank_new"
    __doc__ = "bilibili rank new information"


def init_db():
    """init database"""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
