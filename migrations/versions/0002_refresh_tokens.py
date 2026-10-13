"""refresh 令牌表（§3.3）—— 支撑「轮换时旧的立即失效」与登出吊销。

由 `alembic revision --autogenerate` 产出后**人工复核**：列、唯一约束（jti）、
索引均与 `app/models/account.py::RefreshToken` 一致。

存储选型：落表而不是 Redis（§13 第 10 条 —— 会话吊销初期用 PG 顶掉，接口层不用改）。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_refresh_tokens"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        # 只存 JWT 自带的 jti，不存令牌本体
        sa.Column("jti", sa.String(length=32), nullable=False),
        # active（可用）· rotated（已被轮换替换）· revoked（登出 / 重放吊销）
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_to", sa.String(length=64), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("jti", name=op.f("uq_refresh_tokens_jti")),
    )
    op.create_index(
        "ix_refresh_tokens_user_status", "refresh_tokens", ["user_id", "status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_user_status", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
