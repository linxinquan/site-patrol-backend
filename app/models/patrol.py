"""巡场（§2.3）：patrol_plans / patrol_records（会话型：整份覆盖，后写胜）。"""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SyncColumns, new_id


class PatrolPlan(SyncColumns, Base):
    __tablename__ = "patrol_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False)
    drawing_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drawing_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    floor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    points: Mapped[list] = mapped_column(JSONB, nullable=True)
    total_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_patrol_plans_project_id", "project_id"),
        Index(
            "uq_patrol_plans_client_id",
            "client_id",
            unique=True,
            postgresql_where=text("client_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )


class PatrolRecord(SyncColumns, Base):
    __tablename__ = "patrol_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False)
    drawing_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    drawing_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operator_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dist_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    point_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issue_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    track: Mapped[list] = mapped_column(JSONB, nullable=True)
    checkins: Mapped[list] = mapped_column(JSONB, nullable=True)
    checkpoint_total: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_patrol_records_project_id", "project_id"),
        Index("ix_patrol_records_plan_id", "plan_id"),
        Index(
            "uq_patrol_records_client_id",
            "client_id",
            unique=True,
            postgresql_where=text("client_id IS NOT NULL AND deleted_at IS NULL"),
        ),
    )
