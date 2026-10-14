# site-patrol-backend

「蓝图落地」工地验收 App 的业务后端。**唯一开发指导是 `docs/BACKEND_ARCHITECTURE.md`（v3.4）**，
选型定稿见 `docs/蓝图落地_后端技术选型（定稿）.md`。本 README 只写怎么把工程跑起来。

技术栈：Python 3.12 + FastAPI + SQLAlchemy 2.0 async（asyncpg）+ Alembic + PostgreSQL + 阿里云 OSS（华南1）。

## 目录

```
app/
  core/       配置（全环境变量）· structlog · scrypt/JWT · 权限点目录 · 统一错误
  db/         ORM 基类与同步公共列 · 异步会话 · 变更流（pg_advisory_xact_lock）
  models/     24 张表 = 客户端建模 16 + 服务端 8
  schemas/    Pydantic v2 模型（即 openapi 契约，前端据此生成 types）
  api/v1/     /api/v1/** 路由（A 客户端业务 / B 后台录入 / C 基础与通道）
migrations/   Alembic（0001 初始建表）
scripts/      seed（专业字典 · 7 个内置角色 · 首个管理员）
```

## 本地开发

```bash
# 0) 起一个本地 PostgreSQL（不依赖集群才能写代码，§12）
docker run -d --name site-pg -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=site_patrol postgres:16

# 1) 安装依赖（--extra dev 带上 ruff，CI 与本地 lint 用同一个版本）
uv sync --extra dev

# 2) 配置（Windows PowerShell 用：Copy-Item .env.example .env）
cp .env.example .env        # 至少改 DATABASE_URL 与 JWT_SECRET

# 3) 建表 + 初始数据
uv run alembic upgrade head
uv run python scripts/seed.py

# 4) 启动
uv run uvicorn app.main:app --reload --port 8000
```

验证：`curl localhost:8000/health` · 接口文档 `http://localhost:8000/docs` · 契约 `http://localhost:8000/openapi.json`。

### 没有 Docker 时：Windows 原生 PostgreSQL

Docker Desktop 依赖虚拟化（BIOS 的 `Intel VT-x` + Windows 的「虚拟机平台」）。**没开虚拟化、或不想装 Docker Desktop** 时，
用 EDB 官方的 **ZIP 免安装版** —— 它是纯文件操作，**不注册 Windows 服务、不写注册表**，卸载只需删目录。

> ⚠️ **不要用 EDB 的 `.exe` 安装包**：它必须把 PG 注册成 Windows 服务（写 `HKLM\...Services`），
> 在禁止写注册表的机器上必然失败。ZIP 版没有这个依赖。

```powershell
$pg = 'D:\tools\PostgreSQL\16\pgsql'   # 按自己的盘改

# 1) 下载并解压（约 311 MB，解压后约 840 MB）
$zip = 'D:\tools\downloads\postgresql-16.12-1-windows-x64-binaries.zip'
New-Item -ItemType Directory -Force -Path 'D:\tools\PostgreSQL\16' | Out-Null
tar.exe -xf $zip -C 'D:\tools\PostgreSQL\16'      # 解压后得到 ...\16\pgsql

# 2) 初始化数据目录（UTF8 编码 + C 排序规则）
Set-Content -Path 'D:\tools\PostgreSQL\pw.txt' -Value 'postgres' -Encoding ascii
& "$pg\bin\initdb.exe" -D 'D:\tools\PostgreSQL\data' -U postgres `
    -A scram-sha-256 --pwfile='D:\tools\PostgreSQL\pw.txt' `
    --encoding=UTF8 --locale=C
Remove-Item 'D:\tools\PostgreSQL\pw.txt'

# 3) 启动 / 停止（ZIP 版没有服务，每次开机要手动 start）
& "$pg\bin\pg_ctl.exe" -D 'D:\tools\PostgreSQL\data' -l 'D:\tools\PostgreSQL\pg.log' start
& "$pg\bin\pg_ctl.exe" -D 'D:\tools\PostgreSQL\data' stop

# 4) 建库（与 .env 的 DATABASE_URL 对应）
$env:PGPASSWORD = 'postgres'
& "$pg\bin\psql.exe" -U postgres -h 127.0.0.1 -c "CREATE DATABASE site_patrol ENCODING 'UTF8' TEMPLATE template0;"
```

> ⚠️ **`--locale` 千万别写 `zh_CN`**：Windows 上它对应系统 locale `Chinese (China)_936.GBK`，
> 会把数据库编码设成 **GBK**，直接违反 §2.1 的 UTF8 要求。要中文排序就靠应用侧，
> 数据库层保持 `--encoding=UTF8 --locale=C`。

免安装版自带 `pgcrypto` 与 `pg_trgm`（`0001_initial_schema` 要 `CREATE EXTENSION`，已验证可用），
与 `.env.example` 的 `DATABASE_URL` 无需改动。

本地自检与 CI 跑的是同两件事：

```bash
uv run ruff check .                # 代码规范（规则集在 pyproject.toml 里钉死）
uv run alembic check               # 模型与迁移是否漂移（需先连上本地 PG）
```

> **`alembic.ini` 必须保持纯 ASCII** —— alembic 用 configparser 按**系统 locale** 读它，
> 在中文 Windows 上一个中文注释就会让所有 alembic 命令崩（GBK 解码失败）。

## 约定（改之前先看）

- **配置全走环境变量**，密钥不入库、不进仓库（§10.2）。
- **日志 JSON 到 stdout**，不写文件（§10.2）。
- 统一响应 `{ ok, data, err:{ code, msg } }`；业务失败一律显式报错，不静默降级。
  **框架抛的错也走这个形状** —— 422 请求校验失败 / 404 路由不存在 / 405 方法不对，
  都由 `app/main.py` 的 handler 收口，前端只需要解析一种结构。
- **写 `changes` 必须走 `app.db.changes.record_change`** —— 它取事务级咨询锁，
  否则客户端会静默丢同步变更（§5.2，本项目最硬的一条结论）。
- 权限点目录是**代码常量**（`app/core/permissions.py`），不建表；角色是数据，加角色不发版。
- 迁移必须向前兼容（新字段可空、不删旧字段）；0001 之后一律 `alembic revision --autogenerate` 并人工复核。
- **访问日志**由 `app/core/middleware.py` 产出，每条请求一行 JSON（method / path / status / 耗时 / 客户端 IP）。
  只记 path 不记 query string、不记请求体；`/health` 降到 `debug`，免得被探针刷屏（§10.2 约束 3）。
- **CORS 由 `ALLOWED_ORIGINS` 控制**（逗号分隔）。生产是同源（Ingress 分流，§10.2 约束 6），
  **留空即不启用**；`APP_ENV=prod` 时填 `*` 会直接拒绝启动（带凭证的通配来源等同放开 CSRF）。
- **契约先行**：`app/api/v1/stub_*.py` 是未实现接口的 501 骨架（§4.8），只给路径级契约、不给模型级契约。
  P1 实现某个接口时：**从 stub 文件删掉对应函数 → 新建真实模块 → 在 `api/v1/__init__.py` 里挂到 `stub_*` 之前**。

## 当前进度

**P0 已完成**（按 §11 v3.3：P0 是纯工程底座，**不新增业务接口**）：

- 工程结构 · 24 张表模型 · Alembic 迁移（0001 建表 + 0002 refresh 令牌表）· seed
- 基础通道：JWT 登录 / 刷新 / me · 权限点目录 · 角色 CRUD（含四条数据约束）
- `/health`（liveness + readiness）· 统一响应与统一错误码
- 工程基线：**统一错误响应**（框架的 422 / 404 / 405 也走 `{ok,data,err}`）·
  ruff 规则集在 `pyproject.toml` 钉死 · CI（`ruff check` + PostgreSQL 上的
  `alembic upgrade head` / `alembic check`）· 镜像用 `uv.lock` 构建（`.dockerignore` 已挡密钥）

**P1 进行中**（§11）：

- ✅ **项目与成员 CRUD**（`POST/GET /projects` · `GET/POST/DELETE /projects/{id}/members`）
  —— 成员是项目可见性的唯一依据（§3.2）。三处按文档既有定论落地：**只对 admin 开放**
  （§4.5「B 类的调用方就是它」）；`projects` 走档案类全量拉取**不写 changes**、
  `memberships` 是同步实体**每次写都 `record_change` 且同事务**（§5.2）；移除成员用软删，
  加回来时恢复同一行（`uniq(user_id, project_id)` 不含 `deleted_at`，新建会撞约束）。
- ✅ **就地建号**（`POST /projects/{id}/members/invite`）—— §4.3 里唯一有复合语义的动作：
  填「姓名 + 手机号 + 单位」，**同一请求里建号 + 建成员关系**并返回可用账号。用户已存在
  但不在本项目时只建成员关系、不重复建号。初始密码**只在响应里返回一次**。
- ⬜ 待做：`GET /users`（用户列表，配合就地建号）· 图纸上传与发布（§2.3 事务语义）·
  缺陷主链与事件状态机 · sync push/pull · 量尺阈值 ·
  **`/ai/vision` 鉴权 / 记账 / 缓存层（§12 列为第一风险：网关当前无鉴权）** ·
  OSS 预签名直传（**等凭据**）· 报告分享 · 通知。

> **seed 之后库里会有 3 个账号**：`admin`（全局操作者）+ `pm_demo` / `dl_demo`（演示用）。
> ⚠️ 两个演示账号**没有任何成员关系** —— 非 admin 的可见性完全由 `memberships` 决定（§3.2），
> 它们登录后 `projects` 是空的。要用起来：建项目 → 把账号加为成员。
> 密码在 seed 输出里打印一次；部署时用 `DEMO_USER_PASSWORD` 统一指定（不给就各自随机）。

## 已知缺口（接手前先知道）

**当前无代码层面的已知缺口** —— P0 底座、§3.3 的 refresh 轮换与吊销、§3.1 的权限快照刷新都已落地（变更记录见架构文档 §14 的 v3.6 / v3.7）。

阻塞都在代码之外，需要运维成员或账号凭据才能推进，逐条列在架构文档 **§13 待定项**：OSS 桶凭据（第 3 条，**卡住 P1 的上传链路**）、域名与正式 TLS 证书（第 1 条，iOS 会直接拒连）、§10.3 的部署五问。
