"""同步变更流写入（§5.2）—— 本项目最硬的一条结论。

`bigserial` 分配严格递增，但可见性由提交时间决定：两个事务可能「先分配、后提交」，
客户端按 seq > cursor 拉取时会永久漏掉那条晚提交的变更（静默丢数据、无任何报错）。

解法：在写 changes 的同一事务开头取事务级咨询锁，使分配顺序 ≡ 提交顺序。
事务结束自动释放，连接池下不会泄漏。写入 QPS 极低，串行化代价可忽略。
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.platform import Change

# 固定的咨询锁键（全局唯一即可）
ADVISORY_LOCK_KEY = 981001


async def record_change(
    session: AsyncSession,
    *,
    project_id: str | None,
    entity: str,
    entity_id: str,
    op: str = "upsert",
) -> int:
    """在同一事务内写入一条变更，返回分配到的 seq。调用方需自行 commit。"""
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": ADVISORY_LOCK_KEY})
    change = Change(project_id=project_id, entity=entity, entity_id=entity_id, op=op)
    session.add(change)
    await session.flush()
    return change.seq
