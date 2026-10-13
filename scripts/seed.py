"""初始数据（可重复执行）：专业字典 + 7 个内置角色 + 首个管理员。

用法：
    uv run alembic upgrade head
    uv run python scripts/seed.py

管理员初始凭据：
    ADMIN_USERNAME（默认 admin）· ADMIN_PASSWORD（未设置时随机生成并打印一次）
"""

import asyncio
import os
import secrets

from sqlalchemy import select

from app.core.permissions import ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
from app.core.security import hash_password
from app.db.session import SessionFactory, dispose_engine
from app.models import Discipline, Role, User

# 内置角色（§4.5）—— seed 只是初始数据，之后的新增 / 改权限点全走后台界面
BUILTIN_ROLES: tuple[tuple[str, str, str, int], ...] = (
    ("admin", "后台管理员（操作者）", "全局操作者，可见性与权限 = 全部", 1),
    ("project_manager", "项目负责人", "本项目全部数据", 10),
    ("discipline_lead", "专业负责人", "本项目 · 本专业", 20),
    ("designer", "设计人员", "本项目 · 本专业", 30),
    ("site_engineer", "驻场工程师", "本项目全部（现场记录）", 40),
    ("contractor", "施工方", "仅指派给自己的缺陷", 50),
    ("viewer", "只读（业主 / 监理）", "本项目 · 只读", 60),
)

# 专业字典（§2.3）：第一版只 structure 一条；扩展必须与客户端 DefectCategory 枚举同步发版
DISCIPLINES: tuple[tuple[str, str, int], ...] = (("structure", "结构", 10),)


async def seed_disciplines(session) -> None:
    for code, name, sort in DISCIPLINES:
        if await session.get(Discipline, code) is None:
            session.add(Discipline(code=code, name=name, sort=sort, is_system=True))


async def seed_roles(session) -> None:
    for code, name, description, sort in BUILTIN_ROLES:
        role = await session.get(Role, code)
        permissions = list(DEFAULT_ROLE_PERMISSIONS.get(code, []))
        if code == "admin":
            permissions = list(ALL_PERMISSIONS)
        if role is None:
            session.add(
                Role(
                    code=code,
                    name=name,
                    description=description,
                    permissions=permissions,
                    sort=sort,
                    is_system=True,
                )
            )
        else:
            # 已存在只补权限点（内置角色的 name / permissions 允许被界面改动，不强制覆盖）
            missing = [p for p in permissions if p not in (role.permissions or [])]
            if missing:
                role.permissions = list(role.permissions or []) + missing


async def seed_admin(session) -> None:
    username = os.getenv("ADMIN_USERNAME", "admin")
    existing = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if existing is not None:
        print(f"[seed] 管理员已存在：{username}")
        return

    password = os.getenv("ADMIN_PASSWORD") or secrets.token_urlsafe(12)
    session.add(
        User(
            name="后台管理员",
            username=username,
            # 全局操作者标记：admin 不进 memberships，可见性 = 全部项目（§4.5）
            role="admin",
            status="active",
            password_hash=hash_password(password),
        )
    )
    print(f"[seed] 已创建管理员：{username} / {password}（请立即修改）")


async def main() -> None:
    async with SessionFactory() as session:
        await seed_disciplines(session)
        await seed_roles(session)
        await seed_admin(session)
        await session.commit()
    await dispose_engine()
    print("[seed] 完成")


if __name__ == "__main__":
    asyncio.run(main())
