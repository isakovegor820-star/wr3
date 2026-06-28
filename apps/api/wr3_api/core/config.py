from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "wr3 API"
    environment: str = "development"
    # Reviewer access (scout autopilot, review queue, disclosure ops). When set,
    # the X-WR3-Reviewer header must equal this token. When unset, the legacy
    # "true" header is honored only in development; outside development reviewer
    # access via header is impossible until a token is configured.
    reviewer_token: str | None = None
    cors_origins: list[str] = ["http://127.0.0.1:3000", "http://localhost:3000"]
    cors_origin_regex: str | None = None
    max_source_bytes: int = 750_000
    etherscan_api_key: str | None = None
    etherscan_v2_base_url: str = "https://api.etherscan.io/v2/api"
    etherscan_v2_enabled: bool = True
    basescan_api_key: str | None = None
    bscscan_api_key: str | None = None
    arbiscan_api_key: str | None = None
    explorer_timeout_seconds: float = 8.0
    explorer_max_retries: int = 2
    explorer_retry_backoff_seconds: float = 0.0
    public_rpc_fallback_enabled: bool = True
    ethereum_rpc_url: str | None = None
    base_rpc_url: str | None = None
    bsc_rpc_url: str | None = None
    arbitrum_rpc_url: str | None = None
    solana_rpc_url: str | None = None
    database_url: str | None = None
    backup_dir: str = "artifacts/backups"
    backup_r2_uri: str | None = None
    backup_encryption_passphrase: str | None = None
    sentry_dsn: str | None = None
    telegram_alert_chat_id: str | None = None
    web_base_url: str = "http://127.0.0.1:3001"
    telegram_webhook_secret: str | None = None
    telegram_bot_token: str | None = None
    telegram_reviewer_user_ids: list[str] = []
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
    poc_fork_rpc_url: str | None = None  # when set + target has a deployed address, run PoC against a live fork
    poc_fork_block: int | None = None  # pin the fork to a block for reproducible exploits
    fuzz_test_limit: int = 50000  # medusa tx budget before giving up on a counterexample
    fuzz_timeout_seconds: int = 45  # wall-clock cap for a single medusa campaign
    llm_provider: str = "disabled"
    llm_model: str = "local-deterministic-triage"
    llm_zdr_required: bool = True
    llm_timeout_seconds: float = 25.0
    # Cost controls for autonomous (scout) operation.
    llm_max_calls_per_day: int = 0  # 0 = unlimited; >0 caps provider calls/day
    llm_kill_switch: bool = False  # force deterministic triage (no LLM calls)
    llm_max_tokens: int = 4000  # triage JSON grows with finding count; avoid truncation
    openrouter_api_key: str | None = None
    navy_api_key: str | None = None
    navy_base_url: str = "https://api.navy/v1"
    solodit_api_base_url: str | None = None
    solodit_api_key: str | None = None
    defillama_hacks_url: str = "https://api.llama.fi/hacks"
    defillama_protocols_url: str = "https://api.llama.fi/protocols"
    # Immunefi bug-bounty scope ingestion (free public feed, no API key).
    immunefi_bounties_url: str = "https://immunefi.com/public-api/bounties.json"
    immunefi_enabled: bool = True
    immunefi_min_payout_usd: float = 50_000
    immunefi_max_targets_per_cycle: int = 8
    immunefi_max_per_program: int = 3
    scout_default_interval_seconds: int = 900
    scout_autopilot_enabled: bool = False
    scout_autopilot_per_chain_limit: int = 3
    scout_autopilot_min_tvl_usd: float = 1_000_000
    scout_autopilot_dedupe_window_hours: int = 24
    scout_autopilot_process_queued: bool = True
    rsshub_base_url: str | None = None
    helius_api_key: str | None = None
    helius_rpc_url: str | None = None
    forta_api_key: str | None = None
    tenderly_api_key: str | None = None
    blocksec_api_key: str | None = None
    resend_api_key: str | None = None
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
