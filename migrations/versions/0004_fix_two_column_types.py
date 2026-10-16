"""修正两处列类型 —— 建表时的类型推断错误，被 demo 数据比对抓出来。

- `drawing_versions.version`：Integer → VARCHAR(32)
  版本号是图面版本号（'V1.0'），不是数字序号。建表时看名字里有个 version 就当整数了。
- `defects.completion`：Float → VARCHAR(32)
  整改进度是文本（'未开始' / '进行中' / '已完成'），不是 0-1 小数。

用 `USING ...::text` 保证转换不丢数据。
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_fix_two_column_types"
down_revision: Union[str, None] = "0003_status_match_client"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "drawing_versions",
        "version",
        existing_type=sa.Integer(),
        type_=sa.String(length=32),
        existing_nullable=False,
        server_default="V1.0",
        postgresql_using="version::text",
    )
    op.alter_column(
        "defects",
        "completion",
        existing_type=sa.Float(),
        type_=sa.String(length=32),
        existing_nullable=True,
        postgresql_using="completion::text",
    )


def downgrade() -> None:
    # 降级只保证结构可回退：'V1.0' 无法安全转回 Integer，
    # 先把非纯数字的置 NULL，避免「升级再降级」时直接失败。
    op.execute("UPDATE drawing_versions SET version = NULL WHERE version !~ '^[0-9]+$'")
    op.execute("UPDATE defects SET completion = NULL WHERE completion IS NOT NULL")
    op.alter_column(
        "drawing_versions",
        "version",
        existing_type=sa.String(length=32),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="version::integer",
    )
    op.alter_column(
        "defects",
        "completion",
        existing_type=sa.String(length=32),
        type_=sa.Float(),
        existing_nullable=True,
        postgresql_using="completion::double precision",
    )
