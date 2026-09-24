"""应用配置：全部来自环境变量（§11.2 约束 2 —— 换集群 / 换实例只改配置）。"""

from functools import lru_cache

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

    @property
    def is_prod(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
