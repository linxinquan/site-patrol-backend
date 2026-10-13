"""账号与组织（§2.3）：orgs / disciplines / users / memberships / roles。"""

from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncColumns, new_id


class Org(Base):
    """参与单位（建设 / 设计 / 施工 / 监理…）—— 档案类，不带同步公共列。"""

    __tablename__ = "orgs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))


class Discipline(Base):
    """专业字典（`code` 与 `defects.category` 复用同一套取值，§2.3）。

    第一版只 seed `structure` 一条；扩展清单必须与客户端 `DefectCategory` 枚举同步发版。
    """

    __tablename__ = "disciplines"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


class User(Base):
    """`name` 是姓名，`username` 是登录名（两者都有）。档案类，客户端只读。"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    org_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 展示用角色（可由 memberships / roles 回填），不作为校验依据
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(512), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", server_default="active")
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Role(Base):
    """角色：名字与权限点映射都是数据，加角色不改代码、不发版（§3.1）。

    约束（由接口层保证，不靠外键报错兜底）：
    1) code 建后不可改；2) is_system 不可删；3) 有成员在用不可删；4) admin 行只读。
    """

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 权限点 code 数组 —— 写入时逐个校验必须在目录内（§3.1）
    permissions: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'")
    )
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Membership(SyncColumns, Base):
    """项目成员 —— 项目可见性的唯一依据（§3.2），三个正交维度：

    职责（role_code + permissions）× 专业（disciplines，空数组 = 不限）× 单位（org_id）。
    `permissions` 是下发给 App 的快照，**不是校验依据**：校验永远现读 roles.permissions。
    """

    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False)
    org_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role_code: Mapped[str] = mapped_column(String(64), nullable=False)
    role_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    disciplines: Mapped[list[str]] = mapped_column(
        ARRAY(String(32)), nullable=False, default=list, server_default=text("'{}'")
    )
    permissions: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", server_default="active")

    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_memberships_user_project"),
        Index("ix_memberships_project_id", "project_id"),
        Index("ix_memberships_role_code", "role_code"),
        # GIN：按专业过滤（「专业负责人只看本专业」）
        Index("ix_memberships_disciplines", "disciplines", postgresql_using="gin"),
        # 幂等：软删行不阻塞同一 client_id 重新写入
        Index(
            "uq_memberships_client_id",
            "client_id",
            unique=True,
            postgresql_where=text("client_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )


class RefreshToken(Base):
    """refresh 令牌及其状态（§3.3：轮换时旧的立即失效 → 落表 + `status`）。

    **只存 `jti`，不存令牌本体** —— `jti` 是 JWT 内置的唯一标识（见 `core/security.py`），
    库里被读走也换不出一个可用的令牌。

    `status` 三态：
    - `active`   可用
    - `rotated`  已被轮换替换（即「旧的立即失效」）
    - `revoked`  登出，或检测到重放而被批量吊销

    已是 `rotated` 的令牌再次被使用 = 重放（正常客户端不会拿旧令牌来刷新），
    此时吊销该用户全部令牌 —— 泄露的旧令牌意味着会话已不可信（§3.3）。

    服务端表：不带同步公共列（客户端不读写会话，§2.2）。
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    jti: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active"
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # 轮换后指向新令牌行；被吊销时为空
    rotated_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_refresh_tokens_user_status", "user_id", "status"),)
