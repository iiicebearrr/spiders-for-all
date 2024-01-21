import execjs
from pydantic import BaseModel, Field, field_validator

from spiders_for_all.conf import settings


class SignData(BaseModel):
    x_s: str = Field(..., validation_alias="X-s", serialization_alias="x-s")
    x_t: int = Field(..., validation_alias="X-t", serialization_alias="x-t")

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


def get_sign(api: str, a1: str) -> SignData:
    try:
        return SignData(**get_execjs().call("get_xs", api, "", a1))
    except Exception:
        raise ValueError(
            f"Can not calculate sign, please check {settings.XHS_SIGN_JS_FILE}"
        )
