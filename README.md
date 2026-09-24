# site-patrol-backend

「蓝图落地」工地验收 App 的业务后端。**唯一开发指导是 `docs/BACKEND_ARCHITECTURE.md`（v3.2）**，
选型定稿见 `docs/蓝图落地_后端技术选型（定稿）.md`。本 README 只写怎么把工程跑起来。

技术栈：Python 3.12 + FastAPI + SQLAlchemy 2.0 async（asyncpg）+ Alembic + PostgreSQL + 阿里云 OSS（华南1）。

## 目录

```
app/
  core/       配置（全环境变量）· structlog · scrypt/JWT · 权限点目录 · 统一错误
  db/         ORM 基类与同步公共列 · 异步会话 · 变更流（pg_advisory_xact_lock）
  models/     23 张表 = 客户端建模 16 + 服务端 7
  schemas/    Pydantic v2 模型（即 openapi 契约，前端据此生成 types）
  api/v1/     /api/v1/** 路由（A 客户端业务 / B 后台录入 / C 基础与通道）
migrations/   Alembic（0001 初始建表）
scripts/      seed（专业字典 · 7 个内置角色 · 首个管理员）
```

## 本地开发

```bash
# 0) 起一个本地 PostgreSQL（不依赖集群才能写代码，§13）
docker run -d --name site-pg -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=site_patrol postgres:16

# 1) 安装依赖
uv sync

# 2) 配置
cp .env.example .env        # 至少改 DATABASE_URL 与 JWT_SECRET

# 3) 建表 + 初始数据
uv run alembic upgrade head
uv run python scripts/seed.py

# 4) 启动
uv run uvicorn app.main:app --reload --port 8000
```

验证：`curl localhost:8000/health` · 接口文档 `http://localhost:8000/docs` · 契约 `http://localhost:8000/openapi.json`。

## 约定（改之前先看）

- **配置全走环境变量**，密钥不入库、不进仓库（§11.2）。
- **日志 JSON 到 stdout**，不写文件（§11.2）。
- 统一响应 `{ ok, data, err:{ code, msg } }`；业务失败一律显式报错，不静默降级。
- **写 `changes` 必须走 `app.db.changes.record_change`** —— 它取事务级咨询锁，
  否则客户端会静默丢同步变更（§6.2，本项目最硬的一条结论）。
- 权限点目录是**代码常量**（`app/core/permissions.py`），不建表；角色是数据，加角色不发版。
- 迁移必须向前兼容（新字段可空、不删旧字段）；0001 之后一律 `alembic revision --autogenerate` 并人工复核。

## 当前进度

P0 骨架：工程结构 · 23 张表模型 · Alembic 初始迁移 · JWT 登录/刷新/me · 权限点目录 ·
角色 CRUD（含四条数据约束）· `/health` · seed。

待实现（按 §12 路线）：项目与成员 · 图纸上传与发布（§4.2 事务语义）· 缺陷主链与事件状态机 ·
OSS 预签名直传 · sync push/pull · AI 鉴权记账转发层 · 报告分享 · 通知。
