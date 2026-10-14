"""初始建表：23 张表 + 扩展 + 索引（§2）。

本迁移是「一次性」的建表迁移，直接由 ORM metadata 生成，避免手写 600 行 DDL 产生漂移。
**后续迁移一律用 `alembic revision --autogenerate` 生成并人工复核**，
且必须向前兼容（新增字段可空、不删旧字段，§2.1）。

⚠️ **create_all 建的是「当前代码里」的全部模型表，不是「本迁移时刻」的表**——
所以新加的模型必须登记到 `_LATER_TABLES`，否则从零建库时（CI / 新环境）会先被
create_all 建出来，随后该表的迁移再 `create_table` 就撞 `DuplicateTableError`。
"""

from alembic import op
from sqlalchemy import text

import app.models  # noqa: F401
from app.db.base import Base

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

# 由后续迁移负责创建的表（0001 不得建）
_LATER_TABLES = frozenset({"refresh_tokens"})

_TABLES_AT_THIS_REVISION = [
    table for name, table in Base.metadata.tables.items() if name not in _LATER_TABLES
]


def upgrade() -> None:
    # pgcrypto（gen_random_uuid）· pg_trgm（规范条款 / 缺陷文本模糊召回）
    op.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    op.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, tables=_TABLES_AT_THIS_REVISION)


def downgrade() -> None:
    # 同样只丢本迁移建的表；refresh_tokens 归 0002 的 downgrade（倒序执行时它先跑）
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, tables=_TABLES_AT_THIS_REVISION)
