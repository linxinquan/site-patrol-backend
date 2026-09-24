"""密码哈希（标准库 scrypt，零编译依赖）与 JWT（access 15min / refresh 30d）。"""

import base64
import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import get_settings

# scrypt 参数：n=2**14, r=8, p=1 → 内存约 16MB（maxmem 需 >= 128*n*r）
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32
_SCRYPT_MAXMEM = 64 * 1024 * 1024
_SALT_LEN = 16


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_LEN)
    dk = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
        maxmem=_SCRYPT_MAXMEM,
    )
    return "scrypt${}${}${}${}${}".format(
        _SCRYPT_N,
        _SCRYPT_R,
        _SCRYPT_P,
        base64.b64encode(salt).decode(),
        base64.b64encode(dk).decode(),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, dk_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(dk_b64)
    except (ValueError, TypeError):
        return False

    actual = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=int(n),
        r=int(r),
        p=int(p),
        dklen=_SCRYPT_DKLEN,
        maxmem=_SCRYPT_MAXMEM,
    )
    return hmac.compare_digest(actual, expected)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _encode(token_type: str, subject: str, ttl: timedelta) -> tuple[str, datetime, str]:
    settings = get_settings()
    expires_at = _now() + ttl
    payload = {
        "sub": subject,
        "typ": token_type,
        "jti": uuid.uuid4().hex,
        "iat": int(_now().timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)
    return token, expires_at, payload["jti"]


def create_access_token(user_id: str) -> tuple[str, datetime]:
    settings = get_settings()
    return _encode("access", user_id, timedelta(minutes=settings.access_token_ttl_min))[:2]


def create_refresh_token(user_id: str) -> tuple[str, datetime, str]:
    settings = get_settings()
    return _encode("refresh", user_id, timedelta(days=settings.refresh_token_ttl_days))


def decode_token(token: str, *, expected_type: str | None = None) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except jwt.PyJWTError as exc:  # 过期 / 签名不符 / 结构非法
        raise ValueError(str(exc)) from exc
    if expected_type is not None and payload.get("typ") != expected_type:
        raise ValueError("token type mismatch")
    return payload
