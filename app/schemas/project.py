"""项目与成员模型（§4.3 接口 · §3.2 可见性）。

字段口径对着 §2.3 的表结构写，前端照 `openapi.json` 生成类型，不手写字段名（§4.8）。
"""

from datetime import datetime

from app.schemas.common import CamelModel


class ProjectCreate(CamelModel):
    """项目建档（§4.3「建档（含里程碑 / 参与方）」）。

    `parties` / `milestones` 原样存客户端 toJson()，服务端不解析（§2.3）——
    不给它编细粒度 schema 是有意的：字段随客户端模型演进，服务端猜不准反而会挡住演进。
    """

    name: str
    client: str | None = None
    location: str | None = None
    site_area: float | None = None
    floor_area: float | None = None
    beds: int | None = None
    concept: str | None = None
    lat: float | None = None
    lng: float | None = None
    parties: list = []
    milestones: list = []


class ProjectOut(CamelModel):
    id: str
    name: str
    client: str | None = None
    location: str | None = None
    status: str
    site_area: float | None = None
    floor_area: float | None = None
    beds: int | None = None
    concept: str | None = None
    lat: float | None = None
    lng: float | None = None
    parties: list = []
    milestones: list = []
    measure_thresholds: dict = {}
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MemberCreate(CamelModel):
    """新增成员。

    只收 `role_code`，**不收权限点** —— 快照由服务端按角色当前值填（§3.1：
    权限点由 `roles` 唯一决定，客户端传权限点只会制造第二份事实来源）。
    """

    user_id: str
    role_code: str
    org_id: str | None = None
    # 空数组 = 不限专业（§3.2 / §2.3）
    disciplines: list[str] = []


class MemberOut(CamelModel):
    """成员列表项。`permissions` 是下发快照，校验永远现读 `roles`（§3.1）。"""

    id: str
    user_id: str
    user_name: str | None = None
    project_id: str
    org_id: str | None = None
    role_code: str
    role_name: str | None = None
    disciplines: list[str] = []
    permissions: list[str] = []
    status: str
