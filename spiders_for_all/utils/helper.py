import re
from fake_useragent import UserAgent  # type: ignore

from pathlib import Path

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
