"""DeclarativeBase 与同步公共列（§2.2）。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, MetaData, String, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def new_id() -> str:
    """服务端生成的 id（客户端可写实体由客户端给 ULID，路径见 §2.2）。"""
    return str(uuid4())


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class SyncColumns:
    """客户端可写实体的 7 个公共列 —— 建表即带，事后补极难（§2.2）。

    客户端把这 7 个字段平铺在实体 JSON 顶层，键名为 clientId / version /
    createdAtMs / updatedAtMs / serverUpdatedAtMs / deletedAtMs / createdBy，
    时间以 epoch 毫秒传输，服务端在边界转 timestamptz。
    """

    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    server_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
