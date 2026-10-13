"""应用配置：全部来自环境变量（§10.2 约束 2 —— 换集群 / 换实例只改配置）。"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_env: str = "dev"
    log_level: str = "INFO"

    # 数据库（应用侧唯一依赖）
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/site_patrol"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # JWT（access 15min + refresh 30d 轮换）
    jwt_secret: str = "please-change-me"
    jwt_alg: str = "HS256"
    access_token_ttl_min: int = 15
    refresh_token_ttl_days: int = 30

    # 阿里云 OSS · 华南1（深圳）
    oss_endpoint: str = "https://oss-cn-shenzhen.aliyuncs.com"
    oss_internal_endpoint: str = "https://oss-cn-shenzhen-internal.aliyuncs.com"
    oss_bucket: str = "blueprint-prod"
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_upload_ttl_sec: int = 600
    oss_view_ttl_sec: int = 3600
    oss_share_ttl_sec: int = 900

    # 现有 AI 网关（转发，不搬入）
    ai_gateway_url: str = ""
    ai_gateway_key: str = ""
    ai_upstream_model: str = "qwen-vl-max"
    ai_timeout_sec: int = 180

    # 跨域白名单（逗号分隔）。只在**本地开发**需要：后台 Vite 在 5173、API 在 8000，
    # 不同源会被浏览器拦。生产是同源（Ingress 按路径分流，§10.2 约束 6）——留空即不启用 CORS。
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def is_prod(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _forbid_wildcard_cors_in_prod(self) -> "Settings":
        """生产环境禁止通配来源。

        CORS 的语义是「浏览器同源策略的白名单」。开了 allow_credentials 后，
        `*` 会被部分实现回显成请求方 origin —— 等于对任意站点开放带 Cookie 的请求，
        这就是 CSRF。所以这里直接拒绝启动，而不是等到出事才发现。
        """
        if self.is_prod and "*" in self.cors_origins:
            raise ValueError(
                "生产环境禁止 CORS 通配来源 allowed_origins=*（allow_credentials 下等同放开 CSRF）"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
