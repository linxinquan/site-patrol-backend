"""统一错误码：所有业务失败都返回 { ok:false, err:{ code, msg } }，不静默降级（§8）。"""


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
