"""B 类 · 后台录入接口的骨架路由（§4.3 · 契约先行见 §4.8）。

与 `stub_app.py` 同样的约定：只给路径级契约，模型级契约随 P1 实现补齐；
实现时把函数从这里移走、在 `app/api/v1/__init__.py` 挂新模块。

注意：这一组由**后台界面**调用（Vue 3 + Vite，独立仓库 `site-patrol-admin`），
不是 App 调的 —— 排错时别拿 App 的 token 去打这些接口。
"""

from fastapi import APIRouter

from app.core.errors import NotImplementedYet
from app.schemas.common import ApiResponse

router = APIRouter()

_STUB = {501: {"description": "P1 实现", "model": ApiResponse[None]}}


def _todo(feature: str) -> None:
    raise NotImplementedYet(f"{feature}：契约已出，实现排期见 §11（P1）")


# ---- 组织与用户（含「就地建号」复合语义，§4.3）----


@router.get("/orgs", summary="单位列表", responses=_STUB)
async def list_orgs() -> None:
    _todo("单位列表")


@router.post("/orgs", summary="新建单位", responses=_STUB)
async def create_org() -> None:
    _todo("新建单位")


@router.get("/disciplines", summary="专业字典列表", responses=_STUB)
async def list_disciplines() -> None:
    _todo("专业字典列表")


@router.post("/disciplines", summary="新建专业字典项", responses=_STUB)
async def create_discipline() -> None:
    _todo("新建专业字典项")


@router.get("/users", summary="用户列表", responses=_STUB)
async def list_users() -> None:
    _todo("用户列表")


@router.post("/users", summary="新建用户", responses=_STUB)
async def create_user() -> None:
    _todo("新建用户")


@router.post("/users/{id}/invite", summary="就地建号 / 邀请", responses=_STUB)
async def invite_user(id: str) -> None:
    """「就地建号」：同一请求里建号 + 建成员关系并返回可用账号（§4.3）。

    `users.username` 唯一，需防重。初始凭据策略见 §13 第 6 条（尚未定论）。
    """
    _todo("就地建号 / 邀请")


# ---- 项目与成员（成员是可见性的唯一依据，§3.2）----


@router.post("/projects", summary="建档（含里程碑 / 参与方）", responses=_STUB)
async def create_project() -> None:
    _todo("项目建档")


@router.get("/projects", summary="全部项目视角列表", responses=_STUB)
async def list_projects() -> None:
    _todo("项目列表")


@router.get("/projects/{id}/members", summary="成员列表", responses=_STUB)
async def list_members(id: str) -> None:
    _todo("成员列表")


@router.post("/projects/{id}/members", summary="新增成员", responses=_STUB)
async def add_member(id: str) -> None:
    _todo("新增成员")


@router.delete("/projects/{id}/members", summary="移除成员", responses=_STUB)
async def remove_member(id: str) -> None:
    _todo("移除成员")


@router.get("/projects/{id}/measure-thresholds", summary="量尺阈值", responses=_STUB)
async def get_measure_thresholds(id: str) -> None:
    _todo("读取量尺阈值")


@router.put("/projects/{id}/measure-thresholds", summary="设置量尺阈值", responses=_STUB)
async def put_measure_thresholds(id: str) -> None:
    _todo("设置量尺阈值")


# ---- 图纸与版本（上传链：presign → complete → versions → publish，§6 / §2.3）----


@router.get("/projects/{id}/drawings", summary="图纸列表（含楼层）", responses=_STUB)
async def list_drawings(id: str) -> None:
    _todo("图纸列表")


@router.get("/drawings/{id}", summary="图纸详情", responses=_STUB)
async def get_drawing(id: str) -> None:
    _todo("图纸详情")


@router.get("/drawings/{id}/versions", summary="版本列表", responses=_STUB)
async def list_drawing_versions(id: str) -> None:
    _todo("图纸版本列表")


@router.post("/drawings/{id}/versions", summary="上传完成后登记版本（state=draft）", responses=_STUB)
async def create_drawing_version(id: str) -> None:
    _todo("登记图纸版本")


@router.post("/drawings/{id}/versions/{vid}/publish", summary="发布图纸版本", responses=_STUB)
async def publish_drawing_version(id: str, vid: str) -> None:
    """发布 —— **一个事务内做完 4 件事**，是本项目最容易写错的一处（§2.3）：

    ① 该 drawing 原有 `published` 行 → `archived`；② 目标行 → `published` + published_at/by；
    ③ 回写 `drawings.published_version_id` / `w` / `h` / `hotspots`；④ **同事务写一条 `changes`**。

    违反其中任一条硬约束的后果：App 拉到两张底图 / 状态改了但 App 永远拉不到（静默失效） /
    历史缺陷的 `drawing_version_id` 指向已删行导致坐标回溯断裂 / 双击产生两条无效变更。
    """
    _todo("发布图纸版本")


# ---- 施工进度（写）----


@router.post("/progress-entries", summary="录入施工进度", responses=_STUB)
async def create_progress_entry() -> None:
    """第一版由后台登录态录入 → `source=admin`（§2.3）。"""
    _todo("录入施工进度")
