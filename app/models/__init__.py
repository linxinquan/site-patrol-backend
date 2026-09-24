"""23 张表 = 客户端建模 16 + 服务端 7（§2.3）。"""

from app.models.account import Discipline, Membership, Org, Role, User
from app.models.capture import Capture, MeasureSession, RoomScan
from app.models.defect import DEFECT_ACTIONS, Defect, DefectEvent
from app.models.drawing import Drawing, DrawingVersion, FileRecord
from app.models.patrol import PatrolPlan, PatrolRecord
from app.models.platform import AiCall, AuditLog, Change, Notification
from app.models.project import ProgressEntry, Project, SiteLocation
from app.models.report import Report

__all__ = [
    "DEFECT_ACTIONS",
    "AiCall",
    "AuditLog",
    "Capture",
    "Change",
    "Defect",
    "DefectEvent",
    "Discipline",
    "Drawing",
    "DrawingVersion",
    "FileRecord",
    "MeasureSession",
    "Membership",
    "Notification",
    "Org",
    "PatrolPlan",
    "PatrolRecord",
    "ProgressEntry",
    "Project",
    "Report",
    "Role",
    "RoomScan",
    "SiteLocation",
    "User",
]

# 同步实体名（changes.entity 取值）—— 客户端可写实体，一处定义，防止拼错
SYNC_ENTITIES: tuple[str, ...] = (
    "memberships",
    "defects",
    "captures",
    "measure_sessions",
    "room_scans",
    "patrol_plans",
    "patrol_records",
    "progress_entries",
    "reports",
    "site_locations",
)
