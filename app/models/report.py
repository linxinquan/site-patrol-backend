"""报告归档（§2.3）：reports。

同一份报告导出 PDF / Word / Excel / 网页链接时合并为一条（formats 是数组），不做重复建卡。
客户端归档只存元数据，正文按需重导（§9）。
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncColumns, new_id


class Report(SyncColumns, Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    period: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reporter: Mapped[str | None] = mapped_column(String(100), nullable=True)
    formats: Mapped[list] = mapped_column(JSONB, nullable=True)
    defect_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    open_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    done_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    urgent_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    share_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready", server_default="ready")

    __table_args__ = (
        Index("ix_reports_project_id", "project_id"),
        Index(
            "uq_reports_client_id",
            "client_id",
            unique=True,
            postgresql_where=text("client_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )
