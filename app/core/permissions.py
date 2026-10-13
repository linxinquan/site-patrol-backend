"""权限点目录（§3.1）—— 代码常量，不建表、不是配置项。

增删权限点 = 改代码 + 发版；角色只存 code 数组，中文名与分组只服务界面显示。
`GET /api/v1/permissions` 返回的就是本文件的内容。
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PermissionDef:
    code: str
    name: str
    group: str
    sort: int


# (code, 中文名, 分组, 排序)
PERMISSIONS: tuple[PermissionDef, ...] = (
    # 项目
    PermissionDef("project.read", "查看项目", "项目", 101),
    PermissionDef("project.create", "新建项目", "项目", 102),
    PermissionDef("project.update", "编辑项目", "项目", 103),
    # 成员与账号
    PermissionDef("member.manage", "管理成员", "成员与账号", 201),
    PermissionDef("user.create", "就地建号", "成员与账号", 202),
    # 图纸
    PermissionDef("drawing.read", "查看图纸", "图纸", 301),
    PermissionDef("drawing.manage", "管理图纸", "图纸", 302),
    PermissionDef("drawing.calibrate", "校准图纸", "图纸", 303),
    # 缺陷
    PermissionDef("defect.read", "查看缺陷", "缺陷", 401),
    PermissionDef("defect.create", "上报缺陷", "缺陷", 402),
    PermissionDef("defect.reply", "回复缺陷", "缺陷", 403),
    PermissionDef("defect.update", "修改缺陷状态", "缺陷", 404),
    PermissionDef("defect.assign", "指派缺陷", "缺陷", 405),
    # 现场作业
    PermissionDef("patrol.run", "巡场", "现场作业", 501),
    PermissionDef("measure.write", "量尺", "现场作业", 502),
    PermissionDef("room.write", "量房", "现场作业", 503),
    PermissionDef("capture.create", "拍照验收", "现场作业", 504),
    PermissionDef("siteloc.write", "场地定位", "现场作业", 505),
    # 进度与报告
    PermissionDef("progress.read", "查看进度", "进度与报告", 601),
    PermissionDef("progress.write", "填报进度", "进度与报告", 602),
    PermissionDef("report.export", "导出报告", "进度与报告", 603),
    # 同步
    PermissionDef("sync.push", "同步上行", "同步", 701),
    PermissionDef("sync.pull", "同步下行", "同步", 702),
    # AI
    PermissionDef("ai.invoke", "调用 AI 识别", "AI", 801),
)

PERMISSION_CODES: frozenset[str] = frozenset(p.code for p in PERMISSIONS)

# 后台管理员（admin）恒为全部权限点（§3.1 约束 4）
ALL_PERMISSIONS: tuple[str, ...] = tuple(p.code for p in PERMISSIONS)

# 内置角色的初始权限点（§4.5 矩阵）—— 只是 seed 初值，之后由后台界面维护
DEFAULT_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "admin": ALL_PERMISSIONS,
    "project_manager": (
        "project.read",
        "member.manage",
        "user.create",
        "drawing.read",
        "drawing.manage",
        "defect.read",
        "defect.create",
        "defect.reply",
        "defect.update",
        "defect.assign",
        "patrol.run",
        "measure.write",
        "room.write",
        "capture.create",
        "siteloc.write",
        "progress.read",
        "progress.write",
        "report.export",
        "sync.push",
        "sync.pull",
        "ai.invoke",
    ),
    "discipline_lead": (
        "project.read",
        "drawing.read",
        "defect.read",
        "defect.create",
        "defect.reply",
        "defect.update",
        "defect.assign",
        "progress.read",
        "report.export",
        "sync.push",
        "sync.pull",
        "siteloc.write",
    ),
    "designer": (
        "project.read",
        "drawing.read",
        "defect.read",
        "defect.reply",
        "defect.update",
        "progress.read",
        "sync.push",
        "sync.pull",
        "siteloc.write",
    ),
    "site_engineer": (
        "project.read",
        "drawing.read",
        "defect.read",
        "defect.create",
        "defect.reply",
        "defect.update",
        "defect.assign",
        "patrol.run",
        "measure.write",
        "room.write",
        "capture.create",
        "siteloc.write",
        "progress.read",
        "report.export",
        "sync.push",
        "sync.pull",
        "ai.invoke",
    ),
    "contractor": (
        "project.read",
        "defect.read",
        "defect.reply",
        "progress.read",
        "sync.push",
        "sync.pull",
    ),
    "viewer": (
        "project.read",
        "drawing.read",
        "defect.read",
        "progress.read",
        "report.export",
        "sync.pull",
    ),
}


def is_valid_permission_codes(codes: list[str] | tuple[str, ...] | None) -> bool:
    if codes is None:
        return True
    return all(code in PERMISSION_CODES for code in codes)


def unknown_permission_codes(codes: list[str]) -> list[str]:
    """返回目录外的 code —— 写 roles.permissions 时逐个校验，目录外一律拒绝（§3.1）。"""
    return [code for code in codes if code not in PERMISSION_CODES]
