"""B 类 · 权限点目录（§3.1 · §4.3）—— 只读，来自代码常量，不落库。"""

from fastapi import APIRouter, Depends

from app.api.deps import Principal, require_admin
from app.core.permissions import PERMISSIONS
from app.schemas.common import ApiResponse, ok
from app.schemas.role import PermissionOut

router = APIRouter(prefix="/permissions")


@router.get("", response_model=ApiResponse[list[PermissionOut]], summary="权限点目录（代码常量）")
async def list_permissions(principal: Principal = Depends(require_admin)) -> dict:
    return ok(
        [
            PermissionOut(code=p.code, name=p.name, group=p.group, sort=p.sort)
            for p in PERMISSIONS
        ]
    )
