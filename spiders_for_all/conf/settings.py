import logging
import multiprocessing
import os
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


# NOTE: dm_img_str and dm_cover_img_str seem to be some kind of browser fingerprint, and they seem to be static values
# NOTE: Reference: https://github.com/SocialSisterYi/bilibili-API-collect/issues/868

with env.prefixed("BILIBILI_"):
    BILIBILI_PARAM_DM_IMG_STR = env.str(
        "DM_IMG_STR", "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ"
    )
    BILIBILI_PARAM_DM_COVER_IMG_STR = env.str(
        "DM_COVER_IMG_STR",
        "QU5HTEUgKEludGVsIEluYy4sIEludGVsKFIpIElyaXMoVE0pIFBsdXMgR3JhcGhpY3MgNjU1LCBPcGVuR0wgNC4xKUdvb2dsZSBJbmMuIChJbnRlbCBJbmMuKQ",
    )
    BILIBILI_COOKIE_SESS_DATA = env.str("SESS_DATA", None)

XHS_SIGN_JS_FILE_DEFAULT = BASE_DIR / "spiders_for_all/static" / "xhs.js"

with env.prefixed("XHS_"):
    XHS_COOKIES = env.str("COOKIES", None, subcast_values=str)
    XHS_HEADERS = env.json("HEADERS", "{}", subcast_values=str)
    XHS_SIGN_JS_FILE = Path(env.str("SIGN_JS", str(XHS_SIGN_JS_FILE_DEFAULT)))

REQUEST_MAX_RETRIES = env.int("REQUEST_MAX_RETRIES", 10)
REQUEST_RETRY_INTERVAL = env.int("REQUEST_RETRY_INTERVAL", 30)
REQUEST_RETRY_STEP = env.int("REQUEST_RETRY_STEP", 10)
REQUEST_TIMEOUT = env.int("REQUEST_TIMEOUT", 30)

HTTP_PROXIES = env.json("HTTP_PROXIES", "{}", subcast_values=str)
