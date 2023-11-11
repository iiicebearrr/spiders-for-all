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
        self.api = "https://api.bilibili.com/test"
        self.name = "test_base_spider"
        self.alias = "test"
        self.database_model = TestTable
        self.item_model = VideoModel
        self.response_model = BilibiliVideoResponse

    def get_spider(self) -> Type[spiders.BaseBilibiliSpider]:
        class _TestSpider(spiders.BaseBilibiliSpider):
            api = self.api
            name = self.name
            alias = self.alias
            database_model = self.database_model
            item_model = self.item_model
            response_model = self.response_model

        return _TestSpider

    def test_before_after(self):
        spider = self.get_spider()()
        spider.logger = mock_logger()
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

        spider = self.get_spider()()

        spider.logger = mock_logger()

        response_data = spider.send_request()

        self.assertEqual(mock_requests.request.call_args.args[0], "GET")
        self.assertEqual(mock_requests.request.call_args.args[1], self.api)

        self.assertIsInstance(response_data, self.response_model)

    def test_request_args(self):
        spider = self.get_spider()()
        spider.logger = mock_logger()

        self.assertIn("headers", spider.get_request_args())

    def test_get_items(self):
        spider = self.get_spider()()

        spider.send_request = mock.Mock()
        spider.get_items_from_response = mock.Mock(
            return_value=[TestItem(name=f"test-{i}") for i in range(10)]
        )

        spider.logger = mock_logger()

        items = spider.get_items()

        self.assertIsInstance(next(items), TestItem)  # type: ignore

        self.assertEqual(
            len(list(items)),
            9,
        )

    def test_process_item(self):
        spider = self.get_spider()()

        spider.database_model = mock.Mock()  # type: ignore

        spider.logger = mock_logger()

        item = TestItem(name="test")

        spider.process_item(item, kwargs_1="test", kwargs_2="test")

        spider.database_model.assert_called_once_with(
            name="test",
            kwargs_1="test",
            kwargs_2="test",
        )

    @mock.Mock("bilibili.spiders.Session")
    def test_save_to_db(self, mock_sa_session: mock.Mock):
        mock_session_inst = mock.Mock(
            commit=mock.Mock(),
        )

        mock_sa_session.return_value = mock_session_inst

        spider = self.get_spider()()

        spider.logger = mock_logger()

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

        spider = self.get_spider()()

        spider.logger = mock_logger()

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
        spider = self.get_spider()()

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
        return super().setUp()

    pass


class TestSearchSpider(TestCase):
    pass


class TestPopularSpider(TestCase):
    pass


class TestWeeklySpider(TestCase):
    pass


class TestRankSpider(TestCase):
    pass
