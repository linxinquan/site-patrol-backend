"""A 类 · 客户端业务接口的骨架路由（§4.2 · 契约先行见 §4.8）。

**P1 逐个实现时的做法**：把对应函数从这里删掉 → 在新模块里写真实实现 →
在 `app/api/v1/__init__.py` 里把新模块挂上（顺序排在 stub 之前）。本文件最终会空掉并删除。

⚠️ 本文件只给到**路径级契约**（路径 / 方法 / 路径参数 / 查询参数），
**不含模型级契约**：请求体与响应体的字段要等各模块 P1 实现、§2.3 表结构定稿时才补。
现在补字段只会产生一份「看起来精确、实际会变」的契约，比留空更糟。
"""

from fastapi import APIRouter, Query

from app.core.errors import NotImplementedYet
from app.schemas.common import ApiResponse

router = APIRouter()

_STUB = {501: {"description": "P1 实现", "model": ApiResponse[None]}}


def _todo(feature: str) -> None:
    raise NotImplementedYet(f"{feature}：契约已出，实现排期见 §11（P1）")


# ---- 场地位置（App 拍照页「附近定位」写入，§2.3）----
# ⚠️ 文档写的是 `POST/PATCH /site-locations/{id}` —— POST 也带路径参数 id，与其余 POST 不一致。
# 这里按字面实现，P1 落地前需确认到底是 `POST /site-locations`（body 带 id）还是字面形态。


@router.get("/projects/{id}/site-locations", summary="场地位置列表", responses=_STUB)
async def list_site_locations(id: str) -> None:
    _todo("场地位置列表")


@router.post("/site-locations/{id}", summary="新建场地位置", responses=_STUB)
async def create_site_location(id: str) -> None:
    _todo("新建场地位置")


@router.patch("/site-locations/{id}", summary="更新场地位置", responses=_STUB)
async def update_site_location(id: str) -> None:
    _todo("更新场地位置")


# ---- 缺陷（主链，状态机校验见 §5.4）----


@router.get("/defects", summary="缺陷列表", responses=_STUB)
async def list_defects() -> None:
    _todo("缺陷列表")


@router.post("/defects", summary="新建缺陷", responses=_STUB)
async def create_defect() -> None:
    _todo("新建缺陷")


@router.patch("/defects/{id}", summary="改状态 / 指派", responses=_STUB)
async def update_defect(id: str) -> None:
    _todo("改缺陷状态 / 指派")


@router.post("/defects/{id}/events", summary="缺陷回复 / 事件", responses=_STUB)
async def create_defect_event(id: str) -> None:
    _todo("缺陷事件")


@router.get("/defects/{id}/events", summary="缺陷事件历史", responses=_STUB)
async def list_defect_events(id: str) -> None:
    _todo("缺陷事件历史")


# ---- 巡场 / 量测 / 量房 / 拍照验收（§2.3 会话型数据：整份覆盖、后写胜）----


@router.get("/patrol/plans", summary="巡场计划列表", responses=_STUB)
async def list_patrol_plans() -> None:
    _todo("巡场计划列表")


@router.post("/patrol/plans", summary="新建 / 覆盖巡场计划", responses=_STUB)
async def create_patrol_plan() -> None:
    _todo("新建巡场计划")


@router.get("/patrol/records", summary="巡场记录列表", responses=_STUB)
async def list_patrol_records() -> None:
    _todo("巡场记录列表")


@router.post("/patrol/records", summary="新建 / 覆盖巡场记录", responses=_STUB)
async def create_patrol_record() -> None:
    _todo("新建巡场记录")


@router.get("/measure-sessions", summary="量尺会话列表", responses=_STUB)
async def list_measure_sessions() -> None:
    _todo("量尺会话列表")


@router.post("/measure-sessions", summary="新建 / 覆盖量尺会话", responses=_STUB)
async def create_measure_session() -> None:
    _todo("新建量尺会话")


@router.get("/room-scans", summary="量房记录列表", responses=_STUB)
async def list_room_scans() -> None:
    _todo("量房记录列表")


@router.post("/room-scans", summary="新建 / 覆盖量房记录", responses=_STUB)
async def create_room_scan() -> None:
    _todo("新建量房记录")


@router.get("/captures", summary="拍照验收记录列表", responses=_STUB)
async def list_captures() -> None:
    _todo("拍照验收记录列表")


@router.post("/captures", summary="新建 / 覆盖拍照验收记录", responses=_STUB)
async def create_capture() -> None:
    _todo("新建拍照验收记录")


# ---- 报告（§8：正文客户端生成，服务端只存元数据）----


@router.post("/reports", summary="报告归档", responses=_STUB)
async def create_report() -> None:
    _todo("报告归档")


@router.get("/reports/{id}", summary="报告详情", responses=_STUB)
async def get_report(id: str) -> None:
    _todo("报告详情")


@router.post("/reports/{id}/share", summary="生成分享链接", responses=_STUB)
async def share_report(id: str) -> None:
    _todo("生成分享链接")


# ---- 同步（§5.2 游标方案；写 changes 必须走 app.db.changes.record_change）----


@router.post("/sync/push", summary="上行本地变更", responses=_STUB)
async def sync_push() -> None:
    _todo("同步上行")


@router.get("/sync/pull", summary="按 seq 游标拉取增量", responses=_STUB)
async def sync_pull(
    since_seq: int | None = Query(default=None, description="游标；不传 = 全量重同步"),
    project_id: str | None = Query(default=None, description="限定项目；不传 = 全部可见项目"),
    limit: int = Query(default=200, ge=1, le=1000),
) -> None:
    _todo("同步下行")


# ---- AI（§7：鉴权 / 记账 / 缓存层，排第 1 周 —— 现有网关当前无鉴权）----


@router.post("/ai/vision", summary="AI 视觉识别（缺陷 / 锚物 / 网格 / 目标）", responses=_STUB)
async def ai_vision() -> None:
    _todo("AI 视觉识别")


@router.post("/ai/suggest", summary="整改建议（P3）", responses=_STUB)
async def ai_suggest() -> None:
    _todo("整改建议")


# ---- 通知（§9：推送通道可后补，第一版只做站内消息）----


@router.get("/notifications", summary="站内消息列表", responses=_STUB)
async def list_notifications() -> None:
    _todo("站内消息列表")


@router.post("/notifications/{id}/read", summary="标记已读", responses=_STUB)
async def read_notification(id: str) -> None:
    _todo("标记消息已读")
