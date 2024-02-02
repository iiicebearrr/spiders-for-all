import json

from sqlalchemy import orm
from sqlalchemy.ext.hybrid import hybrid_property

from spiders_for_all.database import schema
from spiders_for_all.spiders.bilibili import models

BaseTable = schema.BaseTable


class BaseBilibiliVideos(BaseTable):
    __abstract__ = True

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

    @hybrid_property
    def owner_info(self) -> models.VideoOwner:
        return models.VideoOwner(**json.loads(self.owner))

    @hybrid_property
    def stat_info(self) -> models.VideoStat:
        return models.VideoStat(**json.loads(self.stat))

    @hybrid_property
    def url(self) -> str:
        return self.short_link_v2


class BaseBilibiliPlay(BaseTable):
    __abstract__ = True

    rank: orm.Mapped[int] = orm.mapped_column(comment="rank of a video")
    rating: orm.Mapped[str] = orm.mapped_column(comment="rating of a video")
    stat: orm.Mapped[str] = orm.mapped_column(comment="stat of a video")
    title: orm.Mapped[str] = orm.mapped_column(comment="title of a video")
    url: orm.Mapped[str] = orm.mapped_column(comment="url of a video")


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


class BilibiliAuthorVideo(BaseTable):
    __tablename__ = "t_bilibili_author_video"
    __doc__ = "bilibili author video information"

    title: orm.Mapped[str] = orm.mapped_column(comment="title of a video")
    aid: orm.Mapped[int] = orm.mapped_column(comment="avid of a video", unique=True)
    bvid: orm.Mapped[str] = orm.mapped_column(comment="bvid of a video", unique=True)
    mid: orm.Mapped[int] = orm.mapped_column(comment="mid of a video")
    comment: orm.Mapped[int] = orm.mapped_column(comment="comment of a video")
    description: orm.Mapped[str] = orm.mapped_column(comment="description of a video")
    is_pay: orm.Mapped[int] = orm.mapped_column(comment="is_pay of a video")
    length: orm.Mapped[int] = orm.mapped_column(comment="length of a video")


class BilibiliAuthorFeed(BaseTable):
    __tablename__ = "t_bilibili_author_feed"
    __doc__ = "bilibili author feed information"

    id_str: orm.Mapped[str] = orm.mapped_column(comment="id_str of a feed")
    pub_time: orm.Mapped[str] = orm.mapped_column(comment="pub_time of a feed")
    action: orm.Mapped[str] = orm.mapped_column(comment="action of a feed")
    jump_url: orm.Mapped[str] = orm.mapped_column(
        comment="jump_url of a feed", nullable=True
    )
    desc: orm.Mapped[str] = orm.mapped_column(comment="desc of a feed", nullable=True)
    comment: orm.Mapped[int] = orm.mapped_column(comment="comment of a feed")
    like: orm.Mapped[int] = orm.mapped_column(comment="like of a feed")
    forward: orm.Mapped[int] = orm.mapped_column(comment="forward of a feed")
