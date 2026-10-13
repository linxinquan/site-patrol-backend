"""统一错误码：所有业务失败都返回 { ok:false, err:{ code, msg } }，不静默降级（§4）。"""


class AppError(Exception):
    status: int = 400
    code: str = "bad_request"

    def __init__(self, msg: str, *, code: str | None = None, status: int | None = None) -> None:
        super().__init__(msg)
        self.msg = msg
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status


class Unauthorized(AppError):
    status = 401
    code = "unauthorized"


class Forbidden(AppError):
    status = 403
    code = "forbidden"


class NotFound(AppError):
    status = 404
    code = "not_found"


class Conflict(AppError):
    status = 409
    code = "conflict"


class InvalidTransition(AppError):
    status = 409
    code = "invalid_transition"


class UpstreamError(AppError):
    status = 502
    code = "upstream_error"


class NotImplementedYet(AppError):
    """契约先行的骨架路由专用（§4.8）—— 路径已在契约里，实现还没到那一期。

    刻意用 501 而不是 404：404 意味着「这条路径不对」，501 意味着「路径对、还没做」，
    前端联调时能一眼分清是自己调错了还是后端还没写完。
    """

    status = 501
    code = "not_implemented"
