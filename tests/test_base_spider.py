from typing import Type
from core.base import Spider, SPIDERS
from unittest import TestCase, mock
from sqlalchemy.orm import DeclarativeBase, mapped_column, MappedColumn
from pydantic import BaseModel
from conf import settings


class _Base(DeclarativeBase):
    pass


class TestTable(_Base):
    __tablename__ = "test"

    id: MappedColumn[int] = mapped_column(primary_key=True)
    name: MappedColumn[str]


class TestItem(BaseModel):
    id: int
    name: str


class TestResponse(BaseModel):
    data: list[TestItem]
    code: int


class TestBaseSpider(TestCase):
    def get_spider(self) -> Type[Spider]:
        class _TestSpider(Spider):
            api = "api"
            name = "test"
            alias = "test_alias"
            database_model = TestTable
            item_model = TestItem
            response_model = TestResponse

            def run(self):
                pass

        return _TestSpider

    def test_init_without_model(self):
        with self.assertRaisesRegex(
            ValueError,
            "Attribute .* is required",
        ):

            class _TestSpider(Spider):
                def run(self):
                    pass

            _TestSpider()

    def test_duplicate_name(self):
        with self.assertRaisesRegex(
            ValueError,
            "Duplicate spider name: test",
        ):

            class _TestSpider(Spider):
                name = "test"
                alias = "test_alias"
                database_model = TestTable
                item_model = TestItem
                response_model = TestResponse

                def run(self):
                    pass

            class _TestSpider_2(Spider):
                name = "test"
                alias = "test_alias_2"
                database_model = TestTable
                item_model = TestItem
                response_model = TestResponse

                def run(self):
                    pass

    def test_duplicate_alias(self):
        with self.assertRaisesRegex(
            ValueError,
            "Duplicate spider alias: test_alias",
        ):

            class _TestSpider(Spider):
                name = "test"
                alias = "test_alias"
                database_model = TestTable
                item_model = TestItem
                response_model = TestResponse

                def run(self):
                    pass

            class _TestSpider_2(Spider):
                name = "test_2"
                alias = "test_alias"
                database_model = TestTable
                item_model = TestItem
                response_model = TestResponse

                def run(self):
                    pass

    def test_register(self):
        s = self.get_spider()
        self.assertIn("test", SPIDERS)
        self.assertIn("test_alias", SPIDERS)
        self.assertEqual(SPIDERS["test"], s)

    def test_log(self):
        def mock_logger() -> mock.Mock:
            logger = mock.Mock()
            logger.log = mock.Mock()
            logger.debug = mock.Mock()
            logger.info = mock.Mock()
            logger.warning = mock.Mock()
            logger.error = mock.Mock()
            logger.critical = mock.Mock()
            return logger

        spider = self.get_spider()()
        spider.logger = mock_logger()
        spider.log("test")
        spider.debug("test")
        spider.info("test")
        spider.warning("test")
        spider.error("test")
        spider.critical("test")
        spider.logger.log.assert_called_once_with(settings.LOG_LEVEL, "test")
        spider.logger.debug.assert_called_once_with("test")
        spider.logger.info.assert_called_once_with("test")
        spider.logger.warning.assert_called_once_with("test")
        spider.logger.error.assert_called_once_with("test", exc_info=True)
        spider.logger.critical.assert_called_once_with("test")

    def test_run(self):
        pass

    def test_string(self):
        spider_cls = self.get_spider()
        self.assertEqual(
            spider_cls.string(),
            f"<Spider {spider_cls.name}({spider_cls.alias}). Database model: {spider_cls.database_model}>",
        )
