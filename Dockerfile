# api 镜像（§11.2）—— 无状态、配置全走环境变量、日志到 stdout。
# 构建：docker build -t <registry>/site-patrol-api:<tag> .
# 运行：docker run -e DATABASE_URL=... -p 8000:8000 <image>
#
# 依赖用「uv + uv.lock」安装（§11.2 约束 8）。不要改回 pip install . ——
# 那会重新解析版本，镜像内容随时间漂移，约束 8 的「可复现」就废了。
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_NO_CACHE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONPATH=/app

WORKDIR /app

# uv 自身也锁版本，否则「uv 变了」也是一种漂移。升级时改这里并跑一次本地构建。
RUN pip install --no-cache-dir "uv==0.12.3"

# 先只拷依赖清单再装：改业务代码命中缓存，不重装依赖。
# --no-install-project：不把项目本身装进 site-packages，代码直接从 /app 导入
#（靠上面的 PYTHONPATH），这样这一步不需要 app/ 源码，保住层缓存。
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./

RUN adduser --disabled-password --no-create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 迁移与发布解耦（§11.2 约束 7）：此处不跑 alembic upgrade，由发布前 Job / 手动执行。
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]