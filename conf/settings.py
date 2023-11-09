import logging
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = True

LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
