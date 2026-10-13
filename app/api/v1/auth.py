"""C 类 · 认证（§3.3 · §4.4）。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, update

from app.api.deps import Principal, admin_permissions, build_grants, get_principal, user_permissions
from app.core.errors import Unauthorized
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db.base import new_id
from app.db.session import DbSession
from app.models import RefreshToken, User
from app.schemas.auth import (
    AuthProfile,
    LoginRequest,
    LoginResult,
    RefreshRequest,
    TokenPair,
    UserBrief,
)
from app.schemas.common import ApiResponse, ok

router = APIRouter(prefix="/auth")


async def _revoke_all(session: DbSession, user_id: str) -> None:
    """把某用户全部**可用**令牌置为已吊销 —— 检测到重放时调用（§3.3）。"""
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.status == "active")
        .values(status="revoked", revoked_at=datetime.now(tz=timezone.utc))
    )
    await session.commit()


@router.post("/login", response_model=ApiResponse[LoginResult], summary="账号密码登录")
async def login(payload: LoginRequest, session: DbSession) -> dict:
    user = (
        await session.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()
    if user is None or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise Unauthorized("用户名或密码错误")

    is_admin = user.role == "admin"
    grants = await build_grants(session, user.id, is_admin)
    permissions = admin_permissions() if is_admin else sorted(await user_permissions(session, user.id))

    access, expires_at = create_access_token(user.id)
    refresh, refresh_exp, refresh_jti = create_refresh_token(user.id)
    # 落表才能做「轮换时旧的立即失效」与登出吊销（§3.3）
    session.add(
        RefreshToken(id=new_id(), user_id=user.id, jti=refresh_jti, expires_at=refresh_exp)
    )

    user.last_login_at = datetime.now(tz=timezone.utc)
    await session.commit()

    return ok(
        LoginResult(
            access=access,
            refresh=refresh,
            expires_at=expires_at,
            user=UserBrief.model_validate(user, from_attributes=True),
            projects=grants,
            permissions=permissions,
        )
    )


@router.post("/refresh", response_model=ApiResponse[TokenPair], summary="刷新令牌（轮换）")
async def refresh(payload: RefreshRequest, session: DbSession) -> dict:
    """轮换 refresh：**签发新令牌，旧的立即失效**（§3.3）。"""
    try:
        decoded = decode_token(payload.refresh, expected_type="refresh")
    except ValueError as exc:
        raise Unauthorized("登录已失效，请重新登录") from exc

    now = datetime.now(tz=timezone.utc)
    row = (
        await session.execute(select(RefreshToken).where(RefreshToken.jti == decoded["jti"]))
    ).scalar_one_or_none()

    if row is None:
        # 没落过库（数据被清过、或别处签发的令牌）—— 同样按失效处理
        raise Unauthorized("登录已失效，请重新登录")

    if row.status == "rotated":
        # 重放：已轮换过的令牌又出现 = 它已泄露，来源不可信 → 吊销该用户全部令牌。
        # 不这么做的话，攻击者拿着偷到的旧令牌能一直换出新令牌，轮换形同虚设。
        await _revoke_all(session, row.user_id)
        raise Unauthorized("登录已失效，请重新登录")

    if row.status != "active" or row.expires_at <= now:
        raise Unauthorized("登录已失效，请重新登录")

    access, expires_at = create_access_token(row.user_id)
    new_refresh, new_exp, new_jti = create_refresh_token(row.user_id)
    new_row = RefreshToken(id=new_id(), user_id=row.user_id, jti=new_jti, expires_at=new_exp)
    session.add(new_row)
    row.status = "rotated"
    row.rotated_to = new_row.id
    await session.commit()
    return ok(TokenPair(access=access, refresh=new_refresh, expires_at=expires_at))


@router.post("/logout", response_model=ApiResponse[None], summary="退出登录")
async def logout(payload: RefreshRequest, session: DbSession) -> dict:
    """吊销当前 refresh 令牌（§3.3）。

    **刻意做成幂等**：令牌本来就无效时（已过期 / 已吊销 / 压根不认识）同样返回成功 ——
    客户端在任何情况下都必须能登出，不能因为令牌已经无效就卡在登不出去的状态。
    """
    try:
        decoded = decode_token(payload.refresh, expected_type="refresh")
    except ValueError:
        return ok(None)

    row = (
        await session.execute(select(RefreshToken).where(RefreshToken.jti == decoded["jti"]))
    ).scalar_one_or_none()
    if row is not None and row.status == "active":
        row.status = "revoked"
        row.revoked_at = datetime.now(tz=timezone.utc)
        await session.commit()
    return ok(None)


@router.get("/me", response_model=ApiResponse[AuthProfile], summary="当前用户 + 项目列表 + 各项目权限")
async def me(
    session: DbSession,
    principal: Principal = Depends(get_principal),
) -> dict:
    user = principal.user
    is_admin = principal.is_admin
    grants = await build_grants(session, user.id, is_admin)
    permissions = admin_permissions() if is_admin else sorted(await user_permissions(session, user.id))
    return ok(
        AuthProfile(
            user=UserBrief.model_validate(user, from_attributes=True),
            is_admin=is_admin,
            projects=grants,
            permissions=permissions,
        )
    )
