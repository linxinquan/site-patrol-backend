"""图纸与版本（§2.3）：drawings / drawing_versions / files。

校准与热点都绑版本：图纸改版 → 新版本行没有 calibration → 旧版本的校准不会被套用，
不做自动坐标迁移。
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, new_id


class Drawing(Base):
    """图纸档案（客户端只读，走 sync/pull 全量覆盖）。

    w / h / hotspots 是「当前发布版本」的冗余快照，权威数据在 drawing_versions。
    """

    __tablename__ = "drawings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    crumb: Mapped[str | None] = mapped_column(String(300), nullable=True)
    variant: Mapped[str | None] = mapped_column(String(64), nullable=True)
    discipline: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_version_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    w: Mapped[float | None] = mapped_column(Float, nullable=True)
    h: Mapped[float | None] = mapped_column(Float, nullable=True)
    hotspots: Mapped[list] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_drawings_project_key"),
        Index("ix_drawings_project_id", "project_id"),
    )


class DrawingVersion(Base):
    """图纸版本。同一 drawing_id 任一时刻只允许一行 state='published'，
    旧版置 archived 并锁定只读（§2.3 由服务层保证）。
    """

    __tablename__ = "drawing_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    drawing_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # 版本号是**字符串**（客户端给的是 'V1.0' 这类图面版本号），不是数字序号。
    # 建表时误定义成 Integer，被 demo 数据比对抓出来。
    version: Mapped[str] = mapped_column(String(32), nullable=False, server_default="V1.0")
    version_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # draft / published / archived
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", server_default="draft")
    base_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    width: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    bounds: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    hotspots: Mapped[list] = mapped_column(JSONB, nullable=True)
    calibration: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    calibration_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # 取当前发布版本
        Index("ix_drawing_versions_drawing_state", "drawing_id", "state"),
    )


class FileRecord(Base):
    """对象存储登记（服务端自有，客户端不建模）。

    文件名 = SHA-256 → 同一张照片重复上传自动去重；不存原始文件名（含中文 / emoji 易编码出错）。
    """

    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # photo / drawing / report / reply_photo / thumb
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exif: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # 去重 / 证据链
        Index("ix_files_sha256", "sha256"),
        Index("ix_files_project_id", "project_id"),
    )
