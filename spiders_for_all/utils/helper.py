import io
import json
import re
import typing as t
from itertools import chain
from pathlib import Path

from fake_useragent import UserAgent  # type: ignore

Ids: t.TypeAlias = str | list[str] | Path | list[Path] | t.BinaryIO

# This useragent is too old. Use from settings
ua = UserAgent(browsers=["chrome"], min_percentage=1.1)

RGX_CHECK_FILENAME = re.compile(r"[\\/:*?\"<>|]")

RGX_SPLIT_IDS = re.compile(r"[\s,\t\n]+")


def user_agent_headers() -> dict[str, str]:
    return {
        "user-agent": ua.random,
    }


def correct_filename(filename: str, replace_with: str = "_") -> str:
    return RGX_CHECK_FILENAME.sub(replace_with, filename)


def rm_tree(pth: Path):
    pth = pth if isinstance(pth, Path) else Path(pth)
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


def javascript_to_dict(raw: str) -> dict[str, t.Any]:
    return json.loads(
        raw.replace("undefined", "null"),
    )


def read_ids_to_list(ids: Ids) -> list[str]:
    match ids:
        case str():
            return list(set(sorted(RGX_SPLIT_IDS.split(ids.strip()))))
        case Path():
            return read_ids_to_list(ids.read_text())
        case t.BinaryIO() | io.BytesIO():
            return read_ids_to_list(ids.read().decode())
        case list():
            return list(
                chain.from_iterable(
                    filter(
                        lambda _bvid: _bvid,
                        map(
                            read_ids_to_list,
                            ids,
                        ),
                    )
                )
            )
        case _:
            raise TypeError(
                f"ids should be str, Path, BinaryIO or list, got {type(ids)}"
            )


if __name__ == "__main__":
    print(ua.random)
