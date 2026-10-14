"""B 类 · 项目与成员（§4.3 · §3.2）—— 成员是项目可见性的唯一依据。

**只对 admin 开放**（§4.5 明写「B 类的调用方就是它」）。矩阵里给其他角色的「读」是
**数据可见性**（图纸 / 缺陷走 `sync/pull` 落到本地），不是让他们调 B 类接口 —— 别照着矩阵
的「读」格给 B 类接口开口子。

两类实体在同步链上的待遇不同，这是 §2.2 公共列约定的直接后果，**别写混**：
- `projects` 是**档案类**：不带 client_id 与软删列，走全量拉取覆盖 → **不写 changes**
- `memberships` 是**客户端可写实体** → **每次写都要 `record_change`，且与写入同事务**（§5.2）

`DELETE /projects/{id}/members/{user_id}` —— §4.3 写的是简写形式 `DELETE /projects/{id}/members`，
但删成员必须指明是谁；`uniq(user_id, project_id)` 恰好支持这种寻址。
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import Principal, require_admin
from app.core.errors import Conflict, NotFound
from app.db.base import new_id
from app.db.changes import record_change
from app.db.session import DbSession
from app.models import Membership, Project, Role, User
from app.schemas.common import ApiResponse, ok
from app.schemas.project import MemberCreate, MemberOut, ProjectCreate, ProjectOut

router = APIRouter()


async def _require_project(session: DbSession, project_id: str) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise NotFound(f"项目不存在：{project_id}")
    return project


async def _active_member(session: DbSession, project_id: str, user_id: str) -> Membership | None:
    """取**未删除**的成员行（软删行不算成员，§2.2）。"""
    row = (
        await session.execute(
            select(Membership).where(
                Membership.project_id == project_id,
                Membership.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if row is None or row.deleted_at is not None:
        return None
    return row


def _member_out(member: Membership, user_name: str | None) -> MemberOut:
    return MemberOut(
        id=member.id,
        user_id=member.user_id,
        user_name=user_name,
        project_id=member.project_id,
        org_id=member.org_id,
        role_code=member.role_code,
        role_name=member.role_name,
        disciplines=list(member.disciplines or []),
        permissions=list(member.permissions or []),
        status=member.status,
    )


@router.post("/projects", response_model=ApiResponse[ProjectOut], summary="项目建档")
async def create_project(
    payload: ProjectCreate,
    session: DbSession,
    principal: Principal = Depends(require_admin),
) -> dict:
    project = Project(
        id=new_id(),
        name=payload.name,
        client=payload.client,
        location=payload.location,
        site_area=payload.site_area,
        floor_area=payload.floor_area,
        beds=payload.beds,
        concept=payload.concept,
        lat=payload.lat,
        lng=payload.lng,
        parties=list(payload.parties),
        milestones=list(payload.milestones),
    )
    session.add(project)
    await session.commit()
    # 档案类 → 不写 changes（§2.2）
    return ok(ProjectOut.model_validate(project, from_attributes=True))


@router.get("/projects", response_model=ApiResponse[list[ProjectOut]], summary="项目列表（全部项目视角）")
async def list_projects(session: DbSession, principal: Principal = Depends(require_admin)) -> dict:
    projects = (
        await session.execute(select(Project).order_by(Project.created_at.desc(), Project.name))
    ).scalars().all()
    return ok([ProjectOut.model_validate(p, from_attributes=True) for p in projects])


@router.get(
    "/projects/{id}/members",
    response_model=ApiResponse[list[MemberOut]],
    summary="成员列表（含姓名与权限点快照）",
)
async def list_members(
    id: str, session: DbSession, principal: Principal = Depends(require_admin)
) -> dict:
    await _require_project(session, id)
    rows = (
        await session.execute(
            select(Membership, User.name)
            .join(User, User.id == Membership.user_id)
            .where(Membership.project_id == id, Membership.deleted_at.is_(None))
            .order_by(Membership.created_at, Membership.id)
        )
    ).all()
    return ok([_member_out(member, name) for member, name in rows])


@router.post("/projects/{id}/members", response_model=ApiResponse[MemberOut], summary="新增成员")
async def add_member(
    id: str,
    payload: MemberCreate,
    session: DbSession,
    principal: Principal = Depends(require_admin),
) -> dict:
    await _require_project(session, id)

    user = await session.get(User, payload.user_id)
    if user is None:
        raise NotFound(f"用户不存在：{payload.user_id}")
    role = await session.get(Role, payload.role_code)
    if role is None:
        raise NotFound(f"角色不存在：{payload.role_code}")

    now = datetime.now(tz=timezone.utc)
    existing = (
        await session.execute(
            select(Membership).where(
                Membership.project_id == id,
                Membership.user_id == payload.user_id,
            )
        )
    ).scalar_one_or_none()

    if existing is not None and existing.deleted_at is None:
        raise Conflict(f"该用户已是项目成员：{payload.user_id}")

    if existing is not None:
        # 移除过的人再加回来 = **恢复同一行**，不是新建：
        # `uniq(user_id, project_id)` 不含 deleted_at，新建必定撞唯一约束。
        existing.role_code = role.code
        existing.role_name = role.name
        existing.org_id = payload.org_id
        existing.disciplines = list(payload.disciplines)
        existing.permissions = list(role.permissions or [])
        existing.status = "active"
        existing.deleted_at = None
        existing.updated_at = now
        member = existing
    else:
        member = Membership(
            id=new_id(),
            user_id=payload.user_id,
            project_id=id,
            org_id=payload.org_id,
            role_code=role.code,
            role_name=role.name,
            disciplines=list(payload.disciplines),
            # 下发快照按角色当前值填，与「改角色时刷新快照」同一条路径（§3.1）
            permissions=list(role.permissions or []),
            created_at=now,
            updated_at=now,
        )
        session.add(member)

    # memberships 在同步流里 —— 与写入同事务，漏了就静默丢变更（§5.2）
    await record_change(
        session, project_id=id, entity="memberships", entity_id=member.id, op="upsert"
    )
    await session.commit()
    return ok(_member_out(member, user.name))


@router.delete(
    "/projects/{id}/members/{user_id}",
    response_model=ApiResponse[None],
    summary="移除成员（软删）",
)
async def remove_member(
    id: str,
    user_id: str,
    session: DbSession,
    principal: Principal = Depends(require_admin),
) -> dict:
    member = await _active_member(session, id, user_id)
    if member is None:
        raise NotFound("该用户不是项目成员")

    now = datetime.now(tz=timezone.utc)
    # 软删：保留痕迹（谁在什么时候被移除本身就是审计信息），且 uq 约束要求复用同一行
    member.deleted_at = now
    member.updated_at = now
    member.status = "removed"
    await record_change(
        session, project_id=id, entity="memberships", entity_id=member.id, op="delete"
    )
    await session.commit()
    return ok(None)
