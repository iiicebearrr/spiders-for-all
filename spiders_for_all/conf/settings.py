import logging
import os
import multiprocessing
from pathlib import Path
from environs import Env

BASE_DIR = Path(__file__).resolve().parent.parent.parent

WORKDIR_ENV = os.environ.get("WORKDIR", default=None)

WORKDIR = Path.cwd() if WORKDIR_ENV is None else Path(WORKDIR_ENV)

DOT_ENV = WORKDIR / ".env"

env = Env()

if DOT_ENV.exists():
    env.read_env(str(WORKDIR / ".env"))
else:
    env.read_env()

DEBUG = env.bool("DEBUG", False)

LOG_LEVEL = env.int("LOG_LEVEL", logging.DEBUG if DEBUG else logging.INFO)

LOG_DIR = WORKDIR / "logs"

DB_DIR = WORKDIR / ".db"

LOG_DIR.mkdir(exist_ok=True)

DB_DIR.mkdir(exist_ok=True)

CPU_COUNT = multiprocessing.cpu_count()
