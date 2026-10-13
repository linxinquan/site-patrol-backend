"""统一响应：{ ok, data, err:{ code, msg } }（§4）。

字段名对外一律 camelCase，与客户端 Dart 模型一致。
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ErrorDetail(CamelModel):
    code: str
    msg: str


class ApiResponse(CamelModel, Generic[T]):
    ok: bool = True
    data: T | None = None
    err: ErrorDetail | None = None


def ok(data: T | None = None) -> dict:
    """构造成功响应体（供 response_model=ApiResponse[...] 的路由返回）。"""
    return {"ok": True, "data": data, "err": None}
