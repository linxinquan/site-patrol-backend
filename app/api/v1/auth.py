"""C 类 · 认证（§3.3 · §4.4）。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import Principal, admin_permissions, build_grants, get_principal, user_permissions
from app.core.errors import Unauthorized
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.db.session import DbSession
from app.models import User
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
    refresh, _, _ = create_refresh_token(user.id)

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
async def refresh(payload: RefreshRequest) -> dict:
    try:
        decoded = decode_token(payload.refresh, expected_type="refresh")
    except ValueError as exc:
        raise Unauthorized("登录已失效，请重新登录") from exc

    # TODO(§3.3)：refresh 轮换要求「旧的立即失效」。第一版不装 Redis 且表清单里没有令牌表，
    # 此处仅签发新令牌。落库吊销方案待定（refresh_tokens 表 / Redis 二选一）后补。
    access, expires_at = create_access_token(decoded["sub"])
    new_refresh, _, _ = create_refresh_token(decoded["sub"])
    return ok(TokenPair(access=access, refresh=new_refresh, expires_at=expires_at))


@router.post("/logout", response_model=ApiResponse[None], summary="退出登录")
async def logout() -> dict:
    # TODO(§3.3)：服务端吊销待令牌存储方案确定后补；当前由客户端丢弃令牌。
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
