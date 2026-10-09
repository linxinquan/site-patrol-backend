"""项目档案（§2.3）：projects / site_locations / progress_entries。

楼层不单独建表 —— 它是图纸（图名）解析出的标签，随 drawings 走。
"""

from datetime import datetime

from sqlalchemy import Date, DateTime, Float, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncColumns, new_id


class Project(Base):
    """档案类：客户端只读，走全量拉取覆盖，因此不带 client_id 与软删列。"""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    client: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", server_default="active")
    site_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    floor_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    beds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    concept: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 参与方 / 里程碑 / 项目级量尺门槛：原样存客户端 toJson()
    parties: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'"))
    milestones: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'"))
    measure_thresholds: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_projects_status", "status"),)


class SiteLocation(SyncColumns, Base):
    """工地定位点：由项目内用户在 App 拍照页「附近定位」填写（客户端可写 → 带公共列）。

    project_id 非空 = 项目专属点位；NULL = 跨项目公共地标。
    它是无信号时手选定位的兜底来源，不构成位置证据。
    """

    __tablename__ = "site_locations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    altitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_site_locations_project_id", "project_id"),
        Index(
            "uq_site_locations_client_id",
            "client_id",
            unique=True,
            postgresql_where=text("client_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )


class ProgressEntry(SyncColumns, Base):
    """施工进度填报。

    `source` 区分填报身份且不得混标：`admin` = 后台界面按里程碑录入（第一版唯一写入路径），
    `contractor` = 施工方免登录自报（分享页，v1.2 起）。
    """

    __tablename__ = "progress_entries"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False)
    milestone_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default="pending"
    )
    date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    photos: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'"))
    declared_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="admin", server_default="admin")

    __table_args__ = (
        Index("ix_progress_entries_project_id", "project_id"),
        Index("ix_progress_entries_milestone_id", "milestone_id"),
        Index(
            "uq_progress_entries_client_id",
            "client_id",
            unique=True,
            postgresql_where=text("client_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )
