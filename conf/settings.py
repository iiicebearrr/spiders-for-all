import logging
from pathlib import Path
from environs import Env

env = Env()
env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = env.bool("DEBUG", False)

LOG_LEVEL = env.int("LOG_LEVEL", logging.DEBUG if DEBUG else logging.INFO)
