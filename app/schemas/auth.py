"""认证相关模型（§3.3 · §5.4）。"""

from datetime import datetime

from app.schemas.common import CamelModel


class LoginRequest(CamelModel):
    username: str
    password: str


class RefreshRequest(CamelModel):
    refresh: str


class TokenPair(CamelModel):
    access: str
    refresh: str
    expires_at: datetime


class UserBrief(CamelModel):
    id: str
    name: str
    username: str
    avatar: str | None = None
    phone: str | None = None
    email: str | None = None
    org_id: str | None = None
    role: str | None = None


class ProjectGrant(CamelModel):
    """某个项目下的授权（App 端据此判定可见性与能力）。"""

    project_id: str
    role_code: str
    role_name: str | None = None
    permissions: list[str] = []
    disciplines: list[str] = []


class LoginResult(CamelModel):
    access: str
    refresh: str
    expires_at: datetime
    user: UserBrief
    projects: list[ProjectGrant] = []
    permissions: list[str] = []


class AuthProfile(CamelModel):
    """GET /auth/me —— 后台界面与 App 的共同入口。"""

    user: UserBrief
    is_admin: bool = False
    projects: list[ProjectGrant] = []
    permissions: list[str] = []
