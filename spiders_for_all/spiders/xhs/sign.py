import json

import execjs
from pydantic import BaseModel, Field, field_validator

from spiders_for_all.conf import settings


class SignData(BaseModel):
    x_s: str = Field(..., validation_alias="X-s", serialization_alias="x-s")
    x_t: int | str = Field(..., validation_alias="X-t", serialization_alias="x-t")

    # x_s_common: str = Field(
    #     ..., validation_alias="X-s-common", serialization_alias="x-s-common"
    # )

    @field_validator("x_t")
    def to_str(cls, v):
        return str(v)


JS = None


def get_execjs():
    global JS

    if JS is None:
        if not settings.XHS_SIGN_JS_FILE.exists():
            raise ValueError(f"File not found: {settings.XHS_SIGN_JS_FILE}")
        JS = execjs.compile(settings.XHS_SIGN_JS_FILE.read_text("utf-8"))

    return JS


def get_sign(api: str, a1: str, data: str | dict | None = None) -> SignData:
    try:
        if data is None:
            data = ""
        elif isinstance(data, dict):
            data = json.dumps(data)
        elif not isinstance(data, str):
            raise ValueError(f"Data must be a dict or a string, but got {type(data)}.")
        return SignData(**get_execjs().call("get_xs", api, data, a1))
    except Exception:
        raise ValueError(
            f"Can not calculate sign, please check {settings.XHS_SIGN_JS_FILE}"
        )
