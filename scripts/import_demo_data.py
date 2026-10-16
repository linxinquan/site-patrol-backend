"""把 Flutter APP 的 demo mock 数据导入后端库（可重复执行）。

数据源默认 `D:\\code\\gongdi\\flutter_app\\demo_data`，可用 `--src` 覆盖。
每份数据的字段口径与派生规则见该目录下的 `README.md`。

用法：
    uv run python scripts/import_demo_data.py --dry-run    # 只报告不写库
    uv run python scripts/import_demo_data.py# 真导入
    uv run python scripts/import_demo_data.py --keep      # 追加，不清空既有表

⚠️ **会清空 demo 涉及的表**（`users` / `refresh_tokens` 不动，登录态不受影响）。
需要保留现有数据时用 `--keep`。
"""

import argparse
import asyncio
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Date, DateTime, Float, Integer, delete, select, text

import app.models  # noqa: F401 —— 让全部模型注册进 metadata
from app.db.base import Base
from app.db.session import SessionFactory, dispose_engine

DEFAULT_SRC = Path(r"D:\code\gongdi\flutter_app\demo_data")

# 导入顺序 = 依赖顺序。库里没有真实 FOREIGN KEY（口径是「不靠外键报错兜底」），
# 但顺序仍按依赖排，避免中间态出现悬空引用。
ORDER: tuple[str, ...] = (
    "disciplines",
    "orgs",
    "projects",
    "drawings",
    "drawing_versions",
    "memberships",
    "defects",
    "defect_events",
    "captures",
    "progress_entries",
    "patrol_plans",
    "patrol_records",
    "reports",
    "site_locations",
)

# 不参与清空：users 是登录账号，refresh_tokens 是会话状态
_PRESERVE_ON_TRUNCATE = {"users", "refresh_tokens"}


# 数值列偶尔会收到 APP 侧的**带单位展示文本**：'12.62万㎡' / '海拔 -4.2m'。
# 直接丢会丢信息，所以提取数字并按中文单位换算；实在提不出就置 NULL 并记账。
_NUM_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(万|亿)?")
_CN_MULT = {"万": 10_000, "亿": 100_000_000}


def coerce(col, value: Any, notes: list[str]) -> Any:
    """按**列类型**决定怎么转换；转不了的记进 notes，不静默丢数据。"""
    if value is None:
        return None

    if isinstance(col.type, DateTime):
        if not isinstance(value, str) or not value.strip():
            notes.append(f"{col.table.name}.{col.name}: {value!r} 不是时间 → NULL")
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            notes.append(f"{col.table.name}.{col.name}: {value!r} 非法 ISO → NULL")
            return None

    # Date 列（progress_entries.date）要的是 datetime.date，不是 datetime
    if isinstance(col.type, Date):
        if not isinstance(value, str):
            notes.append(f"{col.table.name}.{col.name}: {value!r} 不是日期 → NULL")
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            notes.append(f"{col.table.name}.{col.name}: {value!r} 非法日期 → NULL")
            return None

    if isinstance(col.type, (Float, Integer)) and isinstance(value, str):
        # '12.62万㎡' → 126200.0；'64057㎡' → 64057.0；'海拔 -4.2m' → -4.2
        match = _NUM_RE.search(value)
        if match is None:
            notes.append(f"{col.table.name}.{col.name}: {value!r} 提不出数字 → NULL")
            return None
        number = float(match.group(1))
        if match.group(2):
            # round 一下：12.62 * 10000 直接算会得到 126199.99999999999，
            # 面积这种量级的小数噪声没必要留着
            number = round(number * _CN_MULT[match.group(2)], 6)
        return int(number) if isinstance(col.type, Integer) else number

    return value


def load_rows(src: Path, table: str) -> list[dict]:
    path = src / f"{table}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path.name} 不是数组")
    return data


async def resolve_membership_users(session, rows: list[dict], notes: list[str]) -> None:
    """把 `user_ref`（= `users.username`）回填成 `user_id`。

    回答 demo_data/README.md §2③ 那个待确认项：后端 `users.id` 是服务端生成的 uuid
    （`new_id()`），**不是 username**，所以必须按 username join 一次。
    找不到引用的行会让 `user_id` 保持 None —— 上线前必须补齐，否则该成员行没有归属人。
    """
    table = Base.metadata.tables["users"]
    refs = {r["user_ref"] for r in rows if r.get("user_ref")}
    if not refs:
        return
    # 注意方向：我们要 username -> id。写成 dict(...rows) 会把 uuid 当 key、
    # username 当 value（Row 就是个二元组），结果是永远查不到。
    found = {
        username: uid
        for uid, username in (
            await session.execute(
                select(table.c.id, table.c.username).where(table.c.username.in_(refs))
            )
        ).all()
    }
    missing = refs - set(found)
    if missing:
        notes.append(f"users 里找不到 {sorted(missing)}，这些成员行的 user_id 将为空")
    for row in rows:
        ref = row.pop("user_ref", None)
        if ref is not None:
            row["user_id"] = found.get(ref)


async def fill_membership_snapshots(session, rows: list[dict]) -> None:
    """按 `role_code` 回填 `role_name` / `permissions` 快照。

    与 `POST /projects/{id}/members` 同一套口径（§3.1：权限点只有 `roles` 一处事实来源），
    数据里给的空快照不采信。
    """
    roles = Base.metadata.tables["roles"]
    codes = {r["role_code"] for r in rows if r.get("role_code")}
    if not codes:
        return
    got = {
        code: (name, list(perms or []))
        for code, name, perms in (
            await session.execute(
                select(roles.c.code, roles.c.name, roles.c.permissions).where(
                    roles.c.code.in_(codes)
                )
            )
        ).all()
    }
    for row in rows:
        code = row.get("role_code")
        if code in got:
            row["role_name"], row["permissions"] = got[code]
            row["status"] = row.get("status") or "active"


async def preflight(session) -> None:
    """连不上就直接给可操作的提示，别甩一屏 traceback。"""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — 这里要拦住所有连接层异常
        raise SystemExit(
            f"\n[import] 连不上数据库：{exc}\n"
            "先确认 PostgreSQL 是否活着：\n"
            "  & 'D:\\tools\\PostgreSQL\\16\\pgsql\\bin\\pg_ctl.exe' "
            "-D 'D:\\tools\\PostgreSQL\\data' -l 'D:\\tools\\PostgreSQL\\pg.log' start\n"
            "若日志里有 'terminated by exception 0xC0000142'（共享内存分配失败），\n"
            "本机遇到过多次，重启 Windows 通常能恢复。"
        ) from exc


async def wipe(session, tables: list[str]) -> None:
    """逐表 DELETE 清空。

    原本用 `TRUNCATE ... CASCADE`：它要拿ACCESS EXCLUSIVE 锁，而且在本机上直接把
    PG 后端进程搞崩过（0xC0000142，见 §故障记录）。DELETE 只要 ROW EXCLUSIVE，
    慢一点但稳；表之间没有外键约束，靠导入顺序保证一致性就够。
    序列单独重置 —— 只有 `changes.seq` 是 bigserial。
    """
    for name in tables:
        if name in _PRESERVE_ON_TRUNCATE:
            continue
        await session.execute(delete(Base.metadata.tables[name]))
    await session.execute(text("ALTER SEQUENCE changes_seq_seq RESTART WITH 1"))


async def import_table(session, src: Path, table: str) -> tuple[int, list[str]]:
    rows = load_rows(src, table)
    meta = Base.metadata.tables[table]
    cols = {c.name for c in meta.columns}
    notes: list[str] = []

    if table == "memberships":
        await resolve_membership_users(session, rows, notes)
        await fill_membership_snapshots(session, rows)

    payload: list[dict] = []
    for row in rows:
        # 多出来的字段是 APP 展示字段（ts / drawing_key / resp…），库里没有对应列
        record = {k: coerce(meta.c[k], v, notes) for k, v in row.items() if k in cols}
        if "created_at" in cols and not record.get("created_at"):
            record["created_at"] = record.get("server_updated_at") or datetime.now().astimezone()
        if "server_updated_at" in cols and not record.get("server_updated_at"):
            record["server_updated_at"] = record["created_at"]
        payload.append(record)

    if payload:
        await session.execute(meta.insert(), payload)
    return len(payload), notes


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--dry-run", action="store_true", help="只报告不写库")
    ap.add_argument("--keep", action="store_true", help="不清空既有表，直接追加")
    args = ap.parse_args()

    if not args.src.exists():
        raise SystemExit(f"数据目录不存在：{args.src}")

    available = [t for t in ORDER if (args.src / f"{t}.json").exists()]
    missing = [t for t in ORDER if t not in available]
    print(f"[import] 数据源：{args.src}")
    print(f"[import] 找到 {len(available)} 张表" + (f"，缺 {missing}" if missing else ""))

    async with SessionFactory() as session:
        await preflight(session)

        if args.dry_run:
            for table in available:
                meta = Base.metadata.tables[table]
                cols = {c.name for c in meta.columns}
                rows = load_rows(args.src, table)
                dropped = sorted({k for r in rows for k in r} - cols)
                print(f"  {table:<20} {len(rows):>4} 条丢弃字段 {dropped if dropped else '-'}")
            print("[import] dry-run：未写库")
            return

        if not args.keep:
            await wipe(session, available)
            print("[import] 已清空 " + ", ".join(available))

        total = 0
        all_notes: list[str] = []
        for table in available:
            n, notes = await import_table(session, args.src, table)
            total += n
            all_notes.extend(notes)
            print(f"  {table:<20} {n:>4} 条")
        await session.commit()
        print(f"[import] 完成，共 {total} 行")

        if all_notes:
            unique = list(dict.fromkeys(all_notes))
            print(f"\n[import] 值做了转换或置空 {len(all_notes)} 处（不是静默丢弃）：")
            for note in unique:
                print(f"  - {note}")

    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
