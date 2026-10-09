"""应用入口：单一入口 /api/v1/** + GET /health（§1.4 · §11.2）。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger, setup_logging
from app.db.session import dispose_engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level)
    get_logger("startup").info("api starting", env=settings.app_env)
    yield
    await dispose_engine()


app = FastAPI(
    title="site-patrol-backend",
    version="0.1.0",
    description="蓝图落地 · 工地验收 App 业务后端",
    lifespan=lifespan,
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.include_router(api_router)


def _err(status: int, code: str, msg: str) -> JSONResponse:
    """统一错误响应体（§5）—— 所有出口都走它，保证前端只解析一种形状。"""
    return JSONResponse(
        status_code=status,
        content={"ok": False, "data": None, "err": {"code": code, "msg": msg}},
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _err(exc.status, exc.code, exc.msg)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """请求体 / 查询参数校验失败 → 422，但**仍然是 {ok,data,err}**。

    不接管的话 FastAPI 返回 `{"detail": [...]}`，前端按 `err.code` 解析就会炸（§5）。
    """
    errors = exc.errors()
    first = errors[0] if errors else {}
    # loc 形如 ("body", "permissions", 0)：去掉 body/query/path 这些「来源段」，
    # 剩下的就是字段路径（列表下标保留，便于定位第几个元素越界）
    field = ".".join(str(p) for p in first.get("loc", ()) if p not in ("body", "query", "path"))
    detail = str(first.get("msg", "参数校验失败"))
    return _err(422, "validation_error", f"{field}：{detail}" if field else detail)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """框架抛出的 404（路由不存在）/ 405（方法不对）等同样收进统一响应。"""
    code = {
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
    }.get(exc.status_code, "http_error")
    return _err(exc.status_code, code, str(exc.detail))


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    get_logger("error").exception("unhandled error", path=request.url.path)
    return _err(500, "internal_error", "服务内部错误")


def _component_configured(*values: str) -> str:
    return "configured" if all(values) else "not_configured"


@app.get("/health", tags=["运维 C"], summary="健康检查（liveness + readiness）")
async def health() -> JSONResponse:
    """readiness 不通过返回 503 —— 避免把坏实例挂进流量（§11.2 约束 4）。

    DB 做真实连通性探测；OSS / AI 只报配置状态，不打网络请求（探针要廉价且不被上游拖慢）。
    """
    from app.db.session import SessionFactory

    checks: dict[str, str] = {}
    try:
        async with SessionFactory() as session:
            await session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:  # noqa: BLE001 —— 探针要把任何失败都如实报成 503
        checks["db"] = f"error: {exc}"

    checks["oss"] = _component_configured(
        settings.oss_bucket, settings.oss_access_key_id, settings.oss_access_key_secret
    )
    checks["ai_gateway"] = _component_configured(settings.ai_gateway_url)

    healthy = checks["db"] == "ok"
    body = {"status": "ok" if healthy else "degraded", "checks": checks}
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"ok": healthy, "data": body, "err": None},
    )
