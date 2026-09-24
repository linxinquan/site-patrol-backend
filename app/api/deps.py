"""认证与权限依赖（§3.1 · §3.2）。

判定口径：
- `admin` 是唯一破例 —— **不进 memberships**，可见性 = 全部项目，权限 = 全部权限点（§5.5）。
  本实现以 `users.role == 'admin'` 作为全局操作者标记（客户端 `User.role` 同名同义）。
- 其余角色一律由 `memberships` 决定可见性，由 `roles.permissions` **现读**判定权限点；
  `memberships.permissions` 只是下发给 App 的快照，不作校验依据。
- 第一版只按权限点放行，不按专业过滤（§3.1 末注）。
"""

from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Forbidden, Unauthorized
from app.core.permissions import ALL_PERMISSIONS
from app.core.security import decode_token
from app.db.session import DbSession
from app.models import Membership, Role, User
from app.schemas.auth import ProjectGrant

bearer_scheme = HTTPBearer(auto_error=True)


@dataclass(slots=True)
class Principal:
    user: User
    is_admin: bool


async def get_principal(
    session: DbSession,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Principal:
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except ValueError as exc:
        raise Unauthorized("登录已失效，请重新登录") from exc

    user = await session.get(User, payload["sub"])
    if user is None or user.status != "active":
        raise Unauthorized("账号不存在或已停用")
    return Principal(user=user, is_admin=user.role == "admin")


async def get_current_user(principal: Principal = Depends(get_principal)) -> User:
    return principal.user


async def require_admin(principal: Principal = Depends(get_principal)) -> Principal:
    if not principal.is_admin:
        raise Forbidden("仅后台管理员可执行该操作")
    return principal


async def user_permissions(session: AsyncSession, user_id: str) -> set[str]:
    """用户在全部项目上的权限点并集（无项目上下文时使用）。"""
    memberships = (
        await session.execute(select(Membership).where(Membership.user_id == user_id))
    ).scalars().all()
    if not memberships:
        return set()
    roles = (
        await session.execute(select(Role).where(Role.code.in_({m.role_code for m in memberships})))
    ).scalars().all()
    by_code = {r.code: r for r in roles}
    result: set[str] = set()
    for m in memberships:
        role = by_code.get(m.role_code)
        if role is not None:
            result.update(role.permissions or [])
    return result


async def ensure_permission(
    session: AsyncSession,
    principal: Principal,
    code: str,
    project_id: str | None = None,
) -> None:
    """校验权限点；不通过抛 403。roles.permissions 现读，不用快照。"""
    if principal.is_admin:
        return

    if project_id is None:
        if code in await user_permissions(session, principal.user.id):
            return
        raise Forbidden(f"缺少权限点：{code}")

    membership = (
        await session.execute(
            select(Membership).where(
                Membership.user_id == principal.user.id,
                Membership.project_id == project_id,
                Membership.status == "active",
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise Forbidden("不是该项目成员")

    role = await session.get(Role, membership.role_code)
    if role is None or code not in (role.permissions or []):
        raise Forbidden(f"缺少权限点：{code}")


async def build_grants(session: AsyncSession, user_id: str, is_admin: bool) -> list[ProjectGrant]:
    """项目级授权列表（GET /auth/me 的返回内容）。"""
    if is_admin:
        return []
    memberships = (
        await session.execute(
            select(Membership).where(Membership.user_id == user_id, Membership.status == "active")
        )
    ).scalars().all()
    if not memberships:
        return []

    roles = (
        await session.execute(select(Role).where(Role.code.in_({m.role_code for m in memberships})))
    ).scalars().all()
    by_code = {r.code: r for r in roles}

    grants: list[ProjectGrant] = []
    for m in memberships:
        role = by_code.get(m.role_code)
        grants.append(
            ProjectGrant(
                project_id=m.project_id,
                role_code=m.role_code,
                role_name=(role.name if role else m.role_name),
                # 下发快照（App 本地判定用），服务端校验仍现读 roles.permissions
                permissions=list(role.permissions or []) if role else list(m.permissions or []),
                disciplines=list(m.disciplines or []),
            )
        )
    return grants


def admin_permissions() -> list[str]:
    return list(ALL_PERMISSIONS)
