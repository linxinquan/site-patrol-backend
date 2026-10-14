"""初始数据（可重复执行）：专业字典 + 7 个内置角色 + 管理员 + 2 个演示账号。

用法：
    uv run alembic upgrade head
    uv run python scripts/seed.py

初始凭据：
    ADMIN_USERNAME（默认 admin）· ADMIN_PASSWORD（未设置时随机生成并打印一次）
    DEMO_USER_PASSWORD（未设置时两个演示账号各自随机生成并打印一次）

演示账号只有账号、**没有成员关系** —— 可见性由 memberships 决定（§3.2），
要它们能看到项目得先建项目再加成员，详见 DEMO_USERS 处注释。
"""

import asyncio
import os
import secrets

from sqlalchemy import select

from app.core.permissions import ALL_PERMISSIONS, DEFAULT_ROLE_PERMISSIONS
from app.core.security import hash_password
from app.db.base import new_id
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

# 专业字典（§2.3）
# 取值与客户端 `account.dart` 的 `Discipline` 常量**一一对应**（含 `other` 兜底位，
# 客户端 `fromCode` 对未知 code 回落到它）。第一版曾只 seed `structure` 一条，导致
# 客户端按专业过滤时失真 —— 现在按客户端清单补全 7 条。
# 扩展清单必须与客户端 `Discipline` 同步发版。
DISCIPLINES: tuple[tuple[str, str, int], ...] = (
    ("architecture", "建筑", 10),
    ("structure", "结构", 20),
    ("decoration", "装饰", 30),
    ("water", "给排水", 40),
    ("hvac", "暖通", 50),
    ("electric", "电气", 60),
    ("other", "其他", 99),
)

# 演示账号（初始化即有，省得联调时还要现建人）
DEMO_USERS: tuple[tuple[str, str, str], ...] = (
    # (登录名, 姓名, 打算在项目里担任的角色)
    ("pm_demo", "项目负责人（演示）", "project_manager"),
    ("dl_demo", "专业负责人（演示）", "discipline_lead"),
)

# ⚠️ 上面两个账号**不带任何 memberships**：非 admin 用户的可见性完全由 memberships 决定
# （§3.2「成员是可见性的唯一依据」），所以它们登录后 `GET /auth/me` 返回的 projects 是空的。
# 要真正用起来：建项目 → 用 `POST /projects/{id}/members` 把它们加进去。
#
# `users.role` 也**刻意留空**：那一列的注释写着「展示用角色，不作为校验依据」，
# 真正的角色语义由 `memberships.role_code` 表达。往里塞 'project_manager' 只会造出第二份
# 事实来源，迟早和 memberships 对不上。


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


async def seed_demo_users(session) -> None:
    """两个演示账号：项目负责人 / 专业负责人（`DEMO_USERS`）。

    密码统一走 `DEMO_USER_PASSWORD`；没设就各自随机生成并打印一次 —— 与管理员同一个做法，
    库里只存 scrypt 哈希。正式环境不想要演示账号，删掉 `DEMO_USERS` 即可。
    """
    shared = os.getenv("DEMO_USER_PASSWORD")
    for username, name, intended_role in DEMO_USERS:
        existing = (
            await session.execute(select(User).where(User.username == username))
        ).scalar_one_or_none()
        if existing is not None:
            print(f"[seed] 演示账号已存在：{username}")
            continue

        password = shared or secrets.token_urlsafe(12)
        session.add(
            User(
                id=new_id(),
                name=name,
                username=username,
                # role 留空：可见性与角色都由 memberships 决定（§3.2），见 DEMO_USERS 上方注释
                status="active",
                password_hash=hash_password(password),
            )
        )
        print(
            f"[seed] 已创建演示账号：{username} / {password}"
            f"（建项目后把它加为 {intended_role} 才有可见项目）"
        )


async def main() -> None:
    async with SessionFactory() as session:
        await seed_disciplines(session)
        await seed_roles(session)
        await seed_admin(session)
        await seed_demo_users(session)
        await session.commit()
    await dispose_engine()
    print("[seed] 完成")


if __name__ == "__main__":
    asyncio.run(main())
