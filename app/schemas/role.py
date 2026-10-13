"""角色与权限模型（§4.3）。

`RoleUpdate` 刻意不带 code —— 让「建后不可改」（§3.1 约束 1）在类型层面就表达出来。
"""

from app.schemas.common import CamelModel


class PermissionOut(CamelModel):
    """权限点目录项 —— 来自代码常量（app.core.permissions），不在库里。"""

    code: str
    name: str
    group: str
    sort: int


class RoleBase(CamelModel):
    name: str
    description: str | None = None
    permissions: list[str] = []
    sort: int = 0


class RoleCreate(RoleBase):
    code: str


class RoleUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None
    sort: int | None = None


class RoleOut(RoleBase):
    code: str
    is_system: bool = False
    # 派生字段：由 memberships 按 role_code 聚合，库里不存（§2.3）
    member_count: int = 0
