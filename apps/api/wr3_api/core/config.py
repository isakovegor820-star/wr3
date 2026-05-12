from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "wr3 API"
    environment: str = "development"
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]
    max_source_bytes: int = 750_000
    etherscan_api_key: str | None = None
    basescan_api_key: str | None = None
    bscscan_api_key: str | None = None
    arbiscan_api_key: str | None = None
    explorer_timeout_seconds: float = 8.0
    explorer_max_retries: int = 2
    explorer_retry_backoff_seconds: float = 0.0
    database_url: str | None = None
    backup_dir: str = "artifacts/backups"
    backup_r2_uri: str | None = None
    backup_encryption_passphrase: str | None = None
    sentry_dsn: str | None = None
    telegram_alert_chat_id: str | None = None
    usdc_receive_address: str | None = None
    request_finance_invoice_base_url: str | None = None
    polar_checkout_base_url: str | None = None
    web_base_url: str = "http://127.0.0.1:3001"
    telegram_webhook_secret: str | None = None
    telegram_bot_token: str | None = None
    telegram_init_data_max_age_seconds: int = 86_400
    siwe_signature_verification_enabled: bool = False
    email_delivery_enabled: bool = False
    email_magic_link_base_url: str | None = None
    task_backend: str = "local"
    celery_broker_url: str = "redis://127.0.0.1:6379/0"
    celery_result_backend: str = "redis://127.0.0.1:6379/1"
    artifact_dir: str = ".omx/artifacts"
    artifact_encryption_key: str | None = None
    poc_max_attempts: int = 5
    llm_provider: str = "disabled"
    llm_model: str = "local-deterministic-triage"
    llm_zdr_required: bool = True
    llm_timeout_seconds: float = 25.0
    openrouter_api_key: str | None = None
    sandbox_allowed_rpc_hosts: list[str] = ["127.0.0.1", "localhost"]
    sandbox_default_timeout_seconds: int = 120
    webhook_delivery_enabled: bool = False
    webhook_timeout_seconds: float = 5.0
    webhook_signing_secret: str | None = None
    safe_harbor_registry_path: str | None = None
    safe_harbor_registry_json: str | None = None

    model_config = SettingsConfigDict(env_prefix="WR3_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
