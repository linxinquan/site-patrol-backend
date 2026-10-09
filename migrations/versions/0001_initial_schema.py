"""初始建表：23 张表 + 扩展 + 索引（§2）。

本迁移是唯一的「一次性」迁移，直接由 ORM metadata 生成，避免手写 600 行 DDL 产生漂移。
**后续迁移一律用 `alembic revision --autogenerate` 生成并人工复核**，
且必须向前兼容（新增字段可空、不删旧字段，§2.1）。
"""

from alembic import op
from sqlalchemy import text

import app.models  # noqa: F401
from app.db.base import Base

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgcrypto（gen_random_uuid）· pg_trgm（规范条款 / 缺陷文本模糊召回）
    op.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
    op.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
