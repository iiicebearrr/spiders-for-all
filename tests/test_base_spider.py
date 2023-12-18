import secrets
from typing import Type
from unittest import TestCase

from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase, MappedColumn, mapped_column

from spiders_for_all.conf import settings
from spiders_for_all.core.spider import SPIDERS, BaseSpider
from tests._utils import mock_logger


class _Base(DeclarativeBase):
    pass


class Table(_Base):
    __tablename__ = "test"

    id: MappedColumn[int] = mapped_column(primary_key=True)
    name: MappedColumn[str]


class Item(BaseModel):
    id: int
    name: str


class _Response(BaseModel):
    data: list[Item]
    code: int


class TestBaseSpider(TestCase):
    def get_spider(self) -> Type[BaseSpider]:
        class _TestSpider(BaseSpider):
            api = "api"
            name = secrets.token_hex(8)
            alias = secrets.token_hex(16)
            database_model = Table
            item_model = Item
            response_model = _Response

            def run(self):
                pass

        return _TestSpider

    def test_init_without_model(self):
        with self.assertRaisesRegex(
            ValueError,
            "Attribute .* is required",
        ):

            class _TestSpider(BaseSpider):
                def run(self):
                    pass

            _TestSpider()

    def test_duplicate_name(self):
        with self.assertRaisesRegex(
            ValueError,
            "Duplicate spider name: test",
        ):

            class _TestSpider(BaseSpider):
                name = "test"
                alias = "test_alias"
                database_model = Table
                item_model = Item
                response_model = _Response

                def run(self):
                    pass

            class _TestSpider_2(BaseSpider):
                name = "test"
                alias = "test_alias_2"
                database_model = Table
                item_model = Item
                response_model = _Response

                def run(self):
                    pass

    def test_duplicate_alias(self):
        with self.assertRaisesRegex(
            ValueError,
            "Duplicate spider alias: test_alias",
        ):

            class _TestSpider(BaseSpider):
                name = "test"
                alias = "test_alias"
                database_model = Table
                item_model = Item
                response_model = _Response

                def run(self):
                    pass

            class _TestSpider_2(BaseSpider):
                name = "test_2"
                alias = "test_alias"
                database_model = Table
                item_model = Item
                response_model = _Response

                def run(self):
                    pass

    def test_register(self):
        s = self.get_spider()
        self.assertIn(s.name, SPIDERS)
        self.assertIn(s.alias, SPIDERS)
        self.assertEqual(SPIDERS[s.name], s)

    def test_log(self):
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
