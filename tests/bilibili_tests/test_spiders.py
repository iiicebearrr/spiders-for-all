import secrets
from typing import Type

from bilibili import spiders
from unittest import TestCase, mock

from sqlalchemy.orm import mapped_column, MappedColumn
from pydantic import BaseModel

from bilibili.db import Base as BaseTable
from bilibili.models import BilibiliVideoResponse, VideoModel


def mock_logger() -> mock.Mock:
    logger = mock.Mock()
    logger.log = mock.Mock()
    logger.debug = mock.Mock()
    logger.info = mock.Mock()
    logger.warning = mock.Mock()
    logger.error = mock.Mock()
    logger.critical = mock.Mock()
    return logger


class TestTable(BaseTable):
    __tablename__ = "test"

    id: MappedColumn[int] = mapped_column(primary_key=True)
    name: MappedColumn[str]


class TestItem(BaseModel):
    name: str
    bvid: str = "test-bvid"


def get_test_spider(
    api: str,
    name: str,
    alias: str,
    database_model: Type[BaseTable],
    item_model: Type[BaseModel],
    response_model: Type[BaseModel],
    parent: Type[spiders.BaseBilibiliSpider] = spiders.BaseBilibiliSpider,
) -> Type[spiders.BaseBilibiliSpider]:
    test_spider_cls = type(
        "_TestSpider",
        (parent,),
        {
            "api": api,
            "name": name,
            "alias": alias,
            "database_model": database_model,
            "item_model": item_model,
            "response_model": response_model,
        },
    )
    return test_spider_cls


class TestCalculateEndPage(TestCase):
    def test_cal_end_page(self):
        self.assertEqual(
            spiders.calculate_end_page(100, 10, 1),
            10,
        )

        self.assertEqual(
            spiders.calculate_end_page(99, 10, 1),
            10,
        )

        self.assertEqual(spiders.calculate_end_page(100, 10, 2), 11)


class TestBaseBilibiliSpider(TestCase):
    def setUp(self) -> None:
        import secrets

        self.api = "https://api.bilibili.com/test"
        self.name = secrets.token_hex(8)
        self.alias = secrets.token_hex(16)
        self.database_model = TestTable
        self.item_model = VideoModel
        self.response_model = BilibiliVideoResponse

        self.spider = get_test_spider(
            self.api,
            self.name,
            self.alias,
            self.database_model,
            self.item_model,
            self.response_model,
        )()
        self.spider.logger = mock_logger()

    def test_before_after(self):
        spider = self.spider
        spider.before()
        spider.after()

        self.assertEqual(spider.logger.info.call_count, 2)

    @mock.patch("bilibili.spiders.requests")
    def test_send_request(
        self,
        mock_requests: mock.Mock,
    ):
        mock_json_data = {
            "code": 0,
            "data": {
                "list": [
                    {
                        "aid": 1,
                        "bvid": "test",
                        "cid": 1,
                        "desc": "test",
                        "owner": {
                            "mid": 1,
                            "name": "test",
                            "face": "test",
                        },
                        "pubdate": 1,
                        "short_link_v2": "test",
                        "stat": {
                            "aid": 1,
                            "coin": 1,
                            "danmaku": 1,
                            "dislike": 1,
                            "favorite": 1,
                            "his_rank": 1,
                            "like": 1,
                            "now_rank": 1,
                            "reply": 1,
                            "share": 1,
                            "view": 1,
                        },
                        "tid": 1,
                        "title": "test",
                        "tname": "test",
                    }
                ]
            },
            "message": "test",
        }

        mock_requests.request.return_value = mock.Mock(
            status_code=200,
            json=mock.Mock(return_value=mock_json_data),
            raise_for_status=mock.Mock(return_value=None),
        )

        spider = self.spider

        response_data = spider.send_request()

        self.assertEqual(mock_requests.request.call_args.args[0], "GET")
        self.assertEqual(mock_requests.request.call_args.args[1], self.api)

        self.assertIsInstance(response_data, self.response_model)

    def test_request_args(self):
        spider = self.spider

        self.assertIn("headers", spider.get_request_args())

    def test_get_items(self):
        spider = self.spider
        spider.send_request = mock.Mock()
        spider.get_items_from_response = mock.Mock(
            return_value=[TestItem(name=f"test-{i}") for i in range(10)]
        )

        items = spider.get_items()

        self.assertIsInstance(next(items), TestItem)  # type: ignore

        self.assertEqual(
            len(list(items)),
            9,
        )

    def test_process_item(self):
        spider = self.spider
        spider.database_model = mock.Mock()  # type: ignore

        item = TestItem(name="test")

        spider.process_item(item, kwargs_1="test", kwargs_2="test")

        spider.database_model.assert_called_once_with(
            name="test",
            bvid="test-bvid",
            kwargs_1="test",
            kwargs_2="test",
        )

    @mock.Mock("bilibili.spiders.Session")
    def test_save_to_db(self, mock_sa_session: mock.Mock):
        mock_session_inst = mock.Mock(
            commit=mock.Mock(),
        )

        mock_sa_session.return_value = mock_session_inst

        spider = self.spider

        spider.recreate = mock.Mock()

        spider.save_to_db([TestItem(name=f"test-{i}") for i in range(10)])

        mock_sa_session.assert_called_once()

        mock_session_inst.commit.assert_called_once()

        spider.recreate.assert_called_once_with(
            [TestItem(name=f"test-{i}") for i in range(10)],
            session=mock_session_inst,
        )

    @mock.Mock("bilibili.spiders.sa")
    def test_recreate(self, mock_sa: mock.Mock):
        mock_sa.delete = mock.Mock()

        spider = self.spider

        mock_session = mock.Mock(spec="sqlalchemy.orm.session.Session")

        mock_session.execute = mock.Mock()

        mock_session.add_all = mock.Mock()

        spider.process_item = mock.Mock()

        spider.recreate(
            [TestItem(name=f"test-{i}") for i in range(10)], session=mock_session
        )

        mock_sa.delete.assert_called_once_with(spider.database_model)

        mock_session.execute.assert_called_once()

        mock_session.add_all.assert_called_once()

        self.assertEqual(
            spider.process_item.call_count,
            10,
        )

    def test_run(self):
        spider = self.spider
        spider.before = mock.Mock()

        spider.get_items = mock.Mock()

        spider.save_to_db = mock.Mock()

        spider.after = mock.Mock()

        spider.run()

        spider.before.assert_called_once()
        spider.get_items.assert_called_once()
        spider.save_to_db.assert_called_once()
        spider.after.assert_called_once()


class TestPageSpider(TestCase):
    def setUp(self) -> None:
        self.total = 201
        self.page_size = 30
        self.page_number = 1

        self.spider: spiders.BasePageSpider = get_test_spider(
            "https://api.bilibili.com/test",
            secrets.token_hex(8),
            secrets.token_hex(16),
            TestTable,
            TestItem,
            BilibiliVideoResponse,
            parent=spiders.BasePageSpider,
        )(
            total=self.total,
            page_size=self.page_size,
            page_number=self.page_number,
        )  # type: ignore

        self.spider.logger = mock_logger()

    def test_init(self):
        self.assertEqual(self.spider.total, self.total)
        self.assertEqual(self.spider.page_size, self.page_size)
        self.assertEqual(self.spider.page_number, self.page_number)
        self.assertEqual(self.spider.end_page_number, 7)

    def test_get_items_by_page(self):
        # FIXME: Mocking on `send_request` should accept parameters to return data by page number and page size
        self.spider.send_request = mock.Mock()
        self.spider.get_items_from_response = mock.Mock(
            return_value=(TestItem(name=f"test-{i}") for i in range(300))
        )

        items = list(self.spider.get_items())

        self.assertEqual(len(items), self.total)

        # NOTE: send_request and get_items_from_response should be called 7 times
        #       But here we only call it once because of the wrong mocking
        self.spider.send_request.assert_called()
        self.spider.get_items_from_response.assert_called()


class TestSearchSpider(TestCase):
    def setUp(self) -> None:
        self.search_params = {"search_1": 1, "search_2": 2}
        self.spider: spiders.BaseSearchSpider = get_test_spider(
            "https://api.bilibili.com/test",
            secrets.token_hex(8),
            secrets.token_hex(16),
            TestTable,
            TestItem,
            BilibiliVideoResponse,
            parent=spiders.BaseSearchSpider,
        )(**self.search_params)  # type: ignore

    def test_init(self):
        self.assertDictEqual(self.spider.search_params, self.search_params)


class TestPopularSpider(TestCase):
    def setUp(self) -> None:
        self.spider = spiders.PopularSpider()

    def test_request_args(self):
        self.assertIn("params", self.spider.get_request_args())
        self.assertIn("headers", self.spider.get_request_args())

        self.assertEqual(
            self.spider.get_request_args()["params"],
            {
                "pn": self.spider.page_number,
                "ps": self.spider.page_size,
            },
        )

    @mock.patch("bilibili.spiders.sa")
    def test_recreate(self, mock_sa: mock.Mock):
        mock_sa.delete = mock.Mock(where=mock.Mock())

        mock_session = mock.Mock(
            execute=mock.Mock(),
            add_all=mock.Mock(),
        )

        items = [TestItem(name=f"test-{i}") for i in range(10)]

        self.spider.process_item = mock.Mock()

        self.spider.recreate(items, session=mock_session)

        mock_sa.delete.assert_called_once_with(self.spider.database_model)

        mock_session.execute.assert_called_once()

        mock_session.add_all.assert_called_once()


class TestWeeklySpider(TestCase):
    def setUp(self) -> None:
        self.week = 10
        self.spider = spiders.WeeklySpider(week=self.week)

    def test_week_property(self):
        self.assertEqual(self.spider.week, self.week)

        del self.spider.week

        self.spider.search_params = {}

        self.spider.get_all_numbers = mock.Mock()

        self.spider.numbers_list = [1, 2, 3]

        self.assertEqual(self.spider.week, 3)

    def test_request_args(self):
        self.assertIn("params", self.spider.get_request_args())
        self.assertIn("headers", self.spider.get_request_args())

        self.assertEqual(
            self.spider.get_request_args()["params"],
            {
                "number": self.week,
            },
        )

    @mock.patch("bilibili.spiders.sa")
    def test_recreate(self, mock_sa: mock.Mock):
        mock_sa.delete = mock.Mock(where=mock.Mock())

        self.spider.process_item = mock.Mock()

        items = [TestItem(name=f"test-{i}") for i in range(10)]

        mock_session = mock.Mock(
            execute=mock.Mock(),
            add_all=mock.Mock(),
        )

        self.spider.recreate(items, session=mock_session)

        mock_sa.delete.assert_called_once_with(self.spider.database_model)

        mock_session.execute.assert_called_once()

        mock_session.add_all.assert_called_once()

    @mock.patch("bilibili.spiders.requests")
    def test_get_all_weeks(self, mock_requests: mock.Mock):
        spider_cls = spiders.WeeklySpider

        spider_cls.numbers_list = [1, 2, 3]

        self.assertEqual(spider_cls.get_all_numbers(), [1, 2, 3])

        spider_cls.numbers_list = None

        mock_response = mock.Mock()

        mock_response.raise_for_status = mock.Mock()

        mock_response.json = mock.Mock(
            return_value={
                "code": 0,
                "data": {
                    "list": [
                        {
                            "number": 1,
                            "start": 1,
                            "end": 1,
                        },
                        {
                            "number": 2,
                            "start": 2,
                            "end": 2,
                        },
                        {
                            "number": 3,
                            "start": 3,
                            "end": 3,
                        },
                    ]
                },
                "message": "test",
            }
        )

        mock_requests.get = mock.Mock(return_value=mock_response)

        self.assertEqual(spider_cls.get_all_numbers(), [1, 2, 3])

        mock_requests.get.assert_called_once()

        self.assertEqual(mock_requests.get.call_args.args[0], spider_cls.api_list)


class TestPreciousSpider(TestCase):
    def setUp(self) -> None:
        self.spider = spiders.PreciousSpider()

    def test_get_request_args(self):
        self.assertEqual(
            self.spider.get_request_args()["params"],
            {
                "page_size": self.spider.page_size,
                "page": self.spider.page_number,
            },
        )


class TestRankSpider(TestCase):
    def test_rank_spiders(self):
        for _ in (
            spiders.RankAllSpider,
            spiders.RankAnimalSpider,
            spiders.RankAutoTuneSpider,
            spiders.RankCarSpider,
            spiders.RankCartoonSpider,
            spiders.RankCnCartoonSpider,
            spiders.RankCnRelatedSpider,
            spiders.RankDanceSpider,
            spiders.RankDocumentarySpider,
            spiders.RankDramaSpider,
            spiders.RankEntSpider,
            spiders.RankFashionSpider,
            spiders.RankFilmSpider,
            spiders.RankVarietySpider,
            spiders.RankFoodSpider,
            spiders.RankGameSpider,
            spiders.RankNewSpider,
            spiders.RankTvSpider,
            spiders.RankTechSpider,
            spiders.RankSportSpider,
            spiders.RankOriginSpider,
            spiders.RankMusicSpider,
            spiders.RankLifeSpider,
            spiders.RankKnowledgeSpider,
            spiders.RankMovieSpider,
        ):
            pass
