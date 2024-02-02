import hashlib
import random
import time
import urllib.parse

from spiders_for_all.core.client import HttpClient
from spiders_for_all.spiders.bilibili.models import WbiInfo

API_NAV = "https://api.bilibili.com/x/web-interface/nav"


def _get_key(e: str) -> str:
    indices = [
        46,
        47,
        18,
        2,
        53,
        8,
        23,
        32,
        15,
        50,
        10,
        31,
        58,
        3,
        45,
        35,
        27,
        43,
        5,
        49,
        33,
        9,
        42,
        19,
        29,
        28,
        14,
        39,
        12,
        38,
        41,
        13,
        37,
        48,
        7,
        16,
        24,
        55,
        40,
        61,
        26,
        17,
        0,
        1,
        60,
        51,
        30,
        4,
        22,
        25,
        54,
        21,
        56,
        59,
        6,
        63,
        57,
        62,
        11,
        36,
        20,
        34,
        44,
        52,
    ]
    result = []
    for r in indices:
        if r < len(e):
            result.append(e[r])
    return "".join(result)[:32]


def get_wbi_key(client: HttpClient | None = None) -> str:
    if client is None:
        client = HttpClient()
    else:
        client = client.new()

    with client:
        r = client.get(API_NAV)
        wbi_img = r.json().get("data", {})

        if wbi_img is None:
            raise ValueError("wbi_img not found")
    wbi_info = WbiInfo(**wbi_img)

    e = wbi_info.img_key + wbi_info.sub_key

    return _get_key(e)


def get_wrid(query_params: dict[str, str], key: str) -> str:
    wts = round(time.time())

    query_params["wts"] = str(wts)
    query_params = dict(sorted(query_params.items()))
    query_string = urllib.parse.urlencode(query_params) + key
    return hashlib.md5(query_string.encode()).hexdigest()


def get_wrid_with_dm_series(query_params: dict[str, str], key: str) -> str:
    dm_rand = "ABCDEFGHIJK"
    dm_img_list = "[]"
    dm_img_str = "".join(random.sample(dm_rand, 2))
    dm_cover_img_str = "".join(random.sample(dm_rand, 2))
    dm_img_inter = '{"ds":[],"wh":[0,0,0],"of":[0,0,0]}'

    query_params.update(
        {
            "dm_img_list": dm_img_list,
            "dm_img_str": dm_img_str,
            "dm_cover_img_str": dm_cover_img_str,
            "dm_img_inter": dm_img_inter,
        }
    )
    return get_wrid(query_params, key)
