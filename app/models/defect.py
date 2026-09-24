"""缺陷主链（§2.3）：defects / defect_events。

defects 上的 reply* / designer* 是当前态（便于列表查询与报告渲染）；
defect_events 是事件流（审计 + 冲突解决）。两者由同一写路径同时更新。

流程型冲突策略：不「修改记录」，而是追加动作 —— 动作是事实，事实不会冲突。
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncColumns, new_id

# 缺陷事件动作（§2.3）
DEFECT_ACTIONS = (
    "create",
    "update",
    "assign",
    "reply",
    "designer_fix",
    "designer_confirm",
    "onsite",
    "reject",
    "close",
    "reopen",
)


class Defect(SyncColumns, Base):
    __tablename__ = "defects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False)
    drawing_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drawing_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    part: Mapped[str | None] = mapped_column(String(200), nullable=True)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    importance: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", server_default="open")
    anchor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    floor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    building: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gps: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    alt: Mapped[float | None] = mapped_column(Float, nullable=True)
    world_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    world_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    found_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reporter_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reporter: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resp_unit: Mapped[str | None] = mapped_column(String(200), nullable=True)
    resp_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    seed: Mapped[str | None] = mapped_column(String(64), nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_capture_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_capture_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 本地相对路径，只作溯源
    photo_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 取证四要素中的两个（另两个是 GPS 与拍摄时间）—— 必须落库
    photo_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    watermark_serial: Mapped[str | None] = mapped_column(String(128), nullable=True)
    photos: Mapped[list] = mapped_column(JSONB, nullable=True)

    # 当前态：回复
    reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_by_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reply_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reply_photo_file_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 当前态：销项与设计处置
    close_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion: Mapped[float | None] = mapped_column(Float, nullable=True)
    designer_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    designer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    designer_by_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    designer_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_defects_project_status", "project_id", "status"),
        Index("ix_defects_project_updated", "project_id", "server_updated_at"),
        Index("ix_defects_drawing_version", "project_id", "drawing_version_id"),
        # 验收记录 ↔ 缺陷 回流
        Index("ix_defects_source_capture", "source_capture_id"),
        Index(
            "uq_defects_client_id",
            "client_id",
            unique=True,
            postgresql_where=text("client_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )


class DefectEvent(Base):
    """缺陷事件流（审计 + 冲突解决），与 defects 当前态由同一写路径更新。"""

    __tablename__ = "defect_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    defect_id: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_defect_events_defect", "defect_id", "created_at"),)
