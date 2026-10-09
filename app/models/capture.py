"""现场采集（§2.3）：captures / measure_sessions / room_scans。

JSONB 字段直接存客户端 toJson()，服务端不解析几何，只做检索与统计。
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncColumns, new_id


class Capture(SyncColumns, Base):
    """拍照验收记录。

    ai_result = AI 原始识别；confirmed_result = 同一数组加上人工确认 / 转入状态。
    AI 输出不直接改任何工单状态 —— 必须经人工确认后才成为业务状态（§8 红线）。
    """

    __tablename__ = "captures"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False)
    drawing_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drawing_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    floor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    anchor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    world_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    world_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gps: Mapped[str | None] = mapped_column(String(128), nullable=True)
    alt: Mapped[float | None] = mapped_column(Float, nullable=True)
    reporter_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reporter: Mapped[str | None] = mapped_column(String(100), nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    photo_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    confirmed_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_call_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("ix_captures_project_id", "project_id"),
        Index("ix_captures_drawing_version", "project_id", "drawing_version_id"),
        Index(
            "uq_captures_client_id",
            "client_id",
            unique=True,
            postgresql_where=text("client_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )


class MeasureSession(SyncColumns, Base):
    """量尺会话。

    唯一键口径：客户端本地按「项目 + 图纸」一个格子存储，换图纸版本会覆盖同一格子，
    因此服务端 uniq(project_id, drawing_id)，**不把 drawing_version_id 放进唯一键**；
    drawing_version_id 仍照常落库，说明「这次量的是哪版图」。
    """

    __tablename__ = "measure_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False)
    drawing_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drawing_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    floor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tol_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    tol_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    calib: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    items: Mapped[list] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("project_id", "drawing_id", name="uq_measure_sessions_project_drawing"),
        Index(
            "uq_measure_sessions_client_id",
            "client_id",
            unique=True,
            postgresql_where=text("client_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )


class RoomScan(SyncColumns, Base):
    """量房记录（会话型：整份覆盖，后写胜）。"""

    __tablename__ = "room_scans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    room_use: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    walls: Mapped[list] = mapped_column(JSONB, nullable=True)
    closure_delta_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_height_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    drawing_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drawing_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    checks: Mapped[list] = mapped_column(JSONB, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_room_scans_project_id", "project_id"),
        Index(
            "uq_room_scans_client_id",
            "client_id",
            unique=True,
            postgresql_where=text("client_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )
