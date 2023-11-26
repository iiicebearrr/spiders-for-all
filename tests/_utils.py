from unittest import mock


def mock_logger() -> mock.Mock:
    logger = mock.Mock()
    logger.log = mock.Mock()
    logger.debug = mock.Mock()
    logger.info = mock.Mock()
    logger.warning = mock.Mock()
    logger.error = mock.Mock()
    logger.critical = mock.Mock()
    return logger
