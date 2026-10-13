"""HTTP 访问日志（§10.2 约束 3：日志到 stdout / stderr，不写文件、不做轮转）。

为什么放在 logging.py 之外的单独文件：logging.py 只管「怎么格式化」，
这里管「什么值得记」。两者分开，改日志格式不会碰到中间件逻辑。
"""

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

# structlog 的 logger 是惰性代理：这里取一次，首次真正打日志时才会绑定已配置的 processors，
# 所以模块导入早于 setup_logging() 也没问题。
_log = get_logger("access")

# 探针端点：k8s / 负载均衡每几秒打一次，用 debug 级别避免淹没业务日志。
_QUIET_PATHS = frozenset({"/health"})


class AccessLogMiddleware(BaseHTTPMiddleware):
    """每条请求一行 JSON：method / path / status / 耗时 / 客户端 IP。

    两个刻意的取舍：
    - **只记 path，不记 query string** —— query 里可能带 token 一类的东西。
    - **不记请求体** —— 里面有密码、身份证号、工地照片 URL。
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            # finally：即使 handler 抛异常也要留下痕迹，否则 500 恰恰是最需要日志的时候。
            self._emit(request, status_code, started)

    def _emit(self, request: Request, status_code: int, started: float) -> None:
        event = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "client": request.client.host if request.client else None,
        }
        if request.url.path in _QUIET_PATHS:
            _log.debug("http_request", **event)
        else:
            _log.info("http_request", **event)
