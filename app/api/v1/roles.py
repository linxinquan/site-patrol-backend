"""B 类 · 角色管理（§3.1 · §4.3）—— 只对 admin 开放。

四条数据约束（全部「先查引用再删/再改」，不靠外键报错兜底）：
1) code 建后不可改（RoleUpdate 类型上就没有 code）；
2) is_system = true 的内置角色不可删；
3) 有成员在用的角色不可删；
4) `admin` 行只读（权限点恒为全部 24 个）。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import Principal, require_admin
from app.core.errors import AppError, Conflict, Forbidden, NotFound
from app.core.permissions import unknown_permission_codes
from app.db.session import DbSession
from app.models import Membership, Role
from app.schemas.common import ApiResponse, ok
from app.schemas.role import RoleCreate, RoleOut, RoleUpdate

router = APIRouter(prefix="/roles")


async def _member_counts(session: DbSession) -> dict[str, int]:
    rows = (
        await session.execute(
            select(Membership.role_code, func.count(Membership.id)).group_by(Membership.role_code)
        )
    ).all()
    return {code: int(count) for code, count in rows}


def _to_out(role: Role, member_count: int) -> RoleOut:
    return RoleOut(
        code=role.code,
        name=role.name,
        description=role.description,
        permissions=list(role.permissions or []),
        sort=role.sort,
        is_system=role.is_system,
        member_count=member_count,
    )


@router.get("", response_model=ApiResponse[list[RoleOut]], summary="角色列表（含在用人数）")
async def list_roles(
    session: DbSession,
    principal: Principal = Depends(require_admin),
) -> dict:
    roles = (await session.execute(select(Role).order_by(Role.sort, Role.code))).scalars().all()
    counts = await _member_counts(session)
    return ok([_to_out(r, counts.get(r.code, 0)) for r in roles])


@router.post("", response_model=ApiResponse[RoleOut], summary="新增角色")
async def create_role(payload: RoleCreate, session: DbSession, principal=Depends(require_admin)) -> dict:
    unknown = unknown_permission_codes(payload.permissions)
    if unknown:
        raise AppError(f"权限点不在目录内：{', '.join(unknown)}", code="invalid_permission")

    if await session.get(Role, payload.code) is not None:
        raise Conflict(f"角色 code 已存在：{payload.code}")

    role = Role(
        code=payload.code,
        name=payload.name,
        description=payload.description,
        permissions=list(payload.permissions),
        sort=payload.sort,
        is_system=False,
    )
    session.add(role)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise Conflict("角色创建失败（code 冲突）") from exc
    return ok(_to_out(role, 0))


@router.patch("/{code}", response_model=ApiResponse[RoleOut], summary="修改角色（code 不可改）")
async def update_role(
    code: str,
    payload: RoleUpdate,
    session: DbSession,
    principal=Depends(require_admin),
) -> dict:
    role = await session.get(Role, code)
    if role is None:
        raise NotFound(f"角色不存在：{code}")
    if code == "admin":
        raise Forbidden("内置角色 admin 只读（§3.1 约束 4）")

    if payload.permissions is not None:
        unknown = unknown_permission_codes(payload.permissions)
        if unknown:
            raise AppError(f"权限点不在目录内：{', '.join(unknown)}", code="invalid_permission")
        role.permissions = list(payload.permissions)
        # TODO(§3.1)：同一 role_code 的 memberships.permissions 快照需刷新；
        # 第一版 App 不消费权限点，不阻塞，但改角色的路径必须保留这个动作。

    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description
    if payload.sort is not None:
        role.sort = payload.sort
    role.updated_at = datetime.now(tz=timezone.utc)

    await session.commit()
    counts = await _member_counts(session)
    return ok(_to_out(role, counts.get(code, 0)))


@router.delete("/{code}", response_model=ApiResponse[None], summary="删除角色")
async def delete_role(code: str, session: DbSession, principal=Depends(require_admin)) -> dict:
    role = await session.get(Role, code)
    if role is None:
        raise NotFound(f"角色不存在：{code}")
    if role.is_system:
        raise Forbidden("内置角色不可删除（§3.1 约束 2）")

    used = (
        await session.execute(select(func.count(Membership.id)).where(Membership.role_code == code))
    ).scalar_one()
    if used:
        raise Conflict(f"仍有 {used} 名成员在用该角色，不可删除（§3.1 约束 3）")

    await session.delete(role)
    await session.commit()
    return ok(None)
