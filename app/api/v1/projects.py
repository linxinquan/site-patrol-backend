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

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import Principal, require_admin
from app.core.errors import AppError, Conflict, NotFound
from app.core.security import hash_password
from app.db.base import new_id
from app.db.changes import record_change
from app.db.session import DbSession
from app.models import Membership, Project, Role, User
from app.schemas.auth import UserBrief
from app.schemas.common import ApiResponse, ok
from app.schemas.project import (
    InviteCreate,
    InviteResult,
    MemberCreate,
    MemberOut,
    ProjectCreate,
    ProjectOut,
)

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


async def _upsert_membership(
    session: DbSession,
    *,
    project_id: str,
    user_id: str,
    role: Role,
    org_id: str | None,
    disciplines: list[str],
) -> Membership:
    """建或恢复一条成员关系；下发快照按角色**当前值**填（§3.1）。

    已是成员 → 409。被移除过（软删）→ **恢复同一行**而不是新建：
    `uniq(user_id, project_id)` 不含 deleted_at，新建必定撞唯一约束。
    「加成员」与「就地建号」共用这一段，避免两条路径的语义漂移。
    """
    now = datetime.now(tz=timezone.utc)
    existing = (
        await session.execute(
            select(Membership).where(
                Membership.project_id == project_id,
                Membership.user_id == user_id,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        if existing.deleted_at is None:
            raise Conflict(f"该用户已是项目成员：{user_id}")
        existing.role_code = role.code
        existing.role_name = role.name
        existing.org_id = org_id
        existing.disciplines = list(disciplines)
        existing.permissions = list(role.permissions or [])
        existing.status = "active"
        existing.deleted_at = None
        existing.updated_at = now
        return existing

    member = Membership(
        id=new_id(),
        user_id=user_id,
        project_id=project_id,
        org_id=org_id,
        role_code=role.code,
        role_name=role.name,
        disciplines=list(disciplines),
        permissions=list(role.permissions or []),
        created_at=now,
        updated_at=now,
    )
    session.add(member)
    return member


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

    member = await _upsert_membership(
        session,
        project_id=id,
        user_id=payload.user_id,
        role=role,
        org_id=payload.org_id,
        disciplines=payload.disciplines,
    )
    # memberships 在同步流里 —— 与写入同事务，漏了就静默丢变更（§5.2）
    await record_change(
        session, project_id=id, entity="memberships", entity_id=member.id, op="upsert"
    )
    await session.commit()
    return ok(_member_out(member, user.name))


@router.post(
    "/projects/{id}/members/invite",
    response_model=ApiResponse[InviteResult],
    summary="就地建号（同一请求里建号 + 建成员关系）",
)
async def invite_member(
    id: str,
    payload: InviteCreate,
    session: DbSession,
    principal: Principal = Depends(require_admin),
) -> dict:
    """就地建号 —— §4.3 里**唯一有复合语义**的动作：填「姓名 + 手机号 + 单位」，
    若这人还不存在，就在同一个请求里把账号建出来并挂上成员关系，返回可用账号。

    ⚠️ 路径与 §4.3 写的 `POST /users/{id}/invite` 不同：那里的 `{id}` 指什么没说清，而
    「建成员关系」必然要指明是哪个项目。放在 `/projects/{id}/members/invite` 下，
    调用方不必猜 URL 里的 id 是 user 还是 project。

    **初始凭据**：新建账号时随机生成密码，**只在这条响应里返回一次**，库里只存 scrypt 哈希。
    这是沿用 `scripts/seed.py` 建管理员的先例；§13 第 6 条（管理员设初始密码 vs 一次性口令）
    仍待定，改这里要同步改文档。
    """
    await _require_project(session, id)
    role = await session.get(Role, payload.role_code)
    if role is None:
        raise NotFound(f"角色不存在：{payload.role_code}")

    # 先找已有的人：**手机号优先** —— 姓名会重名，登录名才是唯一键
    user = None
    if payload.phone:
        user = (
            await session.execute(select(User).where(User.phone == payload.phone))
        ).scalars().first()
    if user is None and payload.username:
        user = await session.get(User, payload.username)

    created_user = False
    initial_password: str | None = None

    if user is None:
        username = (payload.username or payload.phone or "").strip()
        if not username:
            raise AppError(
                "手机号或登录名至少提供一个 —— 它就是登录名（users.username 唯一，§4.3 要求防重）",
                code="invalid_input",
            )
        if await session.get(User, username) is not None:
            raise Conflict(f"登录名已存在：{username}；该用户已存在，请直接加为成员")
        now = datetime.now(tz=timezone.utc)
        initial_password = secrets.token_urlsafe(12)
        user = User(
            id=new_id(),
            name=payload.name,
            username=username,
            org_id=payload.org_id,
            phone=payload.phone,
            status="active",
            password_hash=hash_password(initial_password),
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        created_user = True

    member = await _upsert_membership(
        session,
        project_id=id,
        user_id=user.id,
        role=role,
        org_id=payload.org_id,
        disciplines=payload.disciplines,
    )
    await record_change(
        session, project_id=id, entity="memberships", entity_id=member.id, op="upsert"
    )
    await session.commit()

    # users 是档案类 → 不进 changes（§2.2）；只有 memberships 进同步流
    return ok(
        InviteResult(
            user=UserBrief.model_validate(user, from_attributes=True),
            member=_member_out(member, user.name),
            created_user=created_user,
            initial_password=initial_password,
        )
    )


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
