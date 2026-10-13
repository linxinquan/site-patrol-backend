"""C 类 · 文件通道的骨架路由（§4.4 · 契约先行见 §4.8）。

这三个接口是**上传链路的服务端那一半**，跨 C / B 两类（§6）：

    POST /files/presign  →  POST /files/complete  →  POST /drawings/{id}/versions  →  .../publish

⚠️ 之前 `oss2` 被摘掉了依赖（它拖 crcmod 源码编译，与 §10.2 约束 8「零原生依赖」冲突）。
**接 OSS 直传时要把 `oss2` 加回 `pyproject.toml`** —— 否则 `import oss2` 会直接失败。
"""

from fastapi import APIRouter

from app.core.errors import NotImplementedYet
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/files")

_STUB = {501: {"description": "P1 实现", "model": ApiResponse[None]}}


def _todo(feature: str) -> None:
    raise NotImplementedYet(f"{feature}：契约已出，实现排期见 §11（P1）")


@router.post("/presign", summary="取上传预签名 URL", responses=_STUB)
async def presign() -> None:
    """下发给客户端一个限定时效的上传凭证（`oss_upload_ttl_sec`，默认 600s）。

    服务端**不中转文件字节**（§10.2 约束 1：无状态，不落本地盘）。
    """
    _todo("取上传预签名 URL")


@router.post("/complete", summary="登记上传完成", responses=_STUB)
async def complete() -> None:
    """客户端上传完毕后回调，落一条 `files` 行，供后续按 id 取签名 URL。"""
    _todo("登记上传完成")


@router.get("/{id}", summary="取文件签名 URL", responses=_STUB)
async def get_file(id: str) -> None:
    """按 `files.id` 返回**限时签名 URL**（`oss_view_ttl_sec`）。

    桶是私有读，客户端永远拿不到永久地址（§6）。
    """
    _todo("取文件签名 URL")
