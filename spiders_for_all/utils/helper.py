import json
import re
import typing as t
from pathlib import Path

from fake_useragent import UserAgent  # type: ignore

ua = UserAgent()


RGX_CHECK_FILENAME = re.compile(r"[\\/:*?\"<>|]")


def user_agent_headers() -> dict[str, str]:
    return {
        "User-Agent": ua.random,
    }


def correct_filename(filename: str, replace_with: str = "_") -> str:
    return RGX_CHECK_FILENAME.sub(replace_with, filename)


def rm_tree(pth: Path):
    pth = Path(pth)
    if not pth.exists():
        return
    for child in pth.glob("*"):
        if child.is_file():
            child.unlink()
        else:
            rm_tree(child)
    pth.rmdir()


def not_none_else(value: t.Any, default: t.Any):
    return value if value is not None else default


def javascript_to_dict(raw: str) -> dict:
    return json.loads(
        raw.replace("undefined", "null"),
    )
