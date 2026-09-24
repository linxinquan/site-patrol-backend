# api 镜像（§11.2）—— 无状态、配置全走环境变量、日志到 stdout。
# 构建：docker build -t <registry>/site-patrol-api:<tag> .
# 运行：docker run -e DATABASE_URL=... -p 8000:8000 <image>
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
COPY alembic.ini ./

RUN pip install --no-cache-dir "uvicorn[standard]" . && \
    adduser --disabled-password --no-create-home appuser && \
    chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

# 迁移与发布解耦（§11.2 约束 7）：此处不跑 alembic upgrade，由发布前 Job / 手动执行。
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
