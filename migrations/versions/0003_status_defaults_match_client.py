"""状态默认值对齐客户端枚举（由 demo 数据比对发现）。

两个字段的 `server_default` 与客户端枚举不一致 —— 客户端的 `fromJson` 缺字段会回落到
自己的初始值，于是「未指定状态」的行在客户端显示成 draft、在服务端却是 open，
两边默认值不同就会让语义悄悄漂移。

- `defects.status`：open → draft（客户端 `enum DefectStatus { draft, doing, done, reject }`）
- `progress_entries.status`：pending → not_started（客户端四个常量之一）

只改默认值，不动已有行的数据（向前兼容，§2.1）。

⚠️ 本文件是**手写**的：当时本机 PostgreSQL 已崩掉（见 README 故障记录），
跑不了 `alembic revision --autogenerate`。改动只有两个 server_default，
可逐行对照 `app/models/defect.py` 与 `app/models/project.py` 复核；
PG 恢复后 `alembic check` 会验证它与模型一致。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_status_defaults_match_client"
down_revision: Union[str, None] = "0002_refresh_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "defects",
        "status",
        existing_type=sa.String(length=32),
        existing_nullable=False,
        server_default="draft",
    )
    op.alter_column(
        "progress_entries",
        "status",
        existing_type=sa.String(length=32),
        existing_nullable=False,
        server_default="not_started",
    )


def downgrade() -> None:
    op.alter_column(
        "defects",
        "status",
        existing_type=sa.String(length=32),
        existing_nullable=False,
        server_default="open",
    )
    op.alter_column(
        "progress_entries",
        "status",
        existing_type=sa.String(length=32),
        existing_nullable=False,
        server_default="pending",
    )
