from unittest import mock, TestCase

from spiders_for_all.bilibili import db


def mock_logger() -> mock.Mock:
    logger = mock.Mock()
    logger.log = mock.Mock()
    logger.debug = mock.Mock()
    logger.info = mock.Mock()
    logger.warning = mock.Mock()
    logger.error = mock.Mock()
    logger.critical = mock.Mock()
    return logger


class DbBindTestCase(TestCase):
    __init_db = False

    @classmethod
    def setUpClass(cls):
        if not cls.__init_db:
            db.init_db()

            cls.__init_db = True
