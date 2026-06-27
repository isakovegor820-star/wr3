from __future__ import annotations

from dataclasses import dataclass

from wr3_api.core.config import Settings, get_settings
from wr3_api.services.rpc import RpcRouter


@dataclass(frozen=True)
class IntegrationDescriptor:
    id: str
    label: str
    priority: str
    category: str
    status: str
    free_mode: str
    used_by: list[str]
    env_vars: list[str]
    next_step: str
    notes: list[str]


class IntegrationStatusService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._rpc = RpcRouter(self._settings)

    def summary(self) -> dict[str, object]:
        integrations = self.integrations()
        counts = {
            "configured": sum(1 for item in integrations if item.status == "configured"),
            "free_fallback": sum(1 for item in integrations if item.status == "free_fallback"),
            "manual": sum(1 for item in integrations if item.status == "manual"),
            "disabled": sum(1 for item in integrations if item.status == "disabled"),
            "blocked": sum(1 for item in integrations if item.status == "blocked"),
        }
        return {
            "status": "ready_for_localhost" if counts["blocked"] == 0 else "needs_external_access",
            "counts": counts,
            "rpc": self._rpc.summary(),
            "integrations": [item.__dict__ for item in integrations],
        }

    def integrations(self) -> list[IntegrationDescriptor]:
        s = self._settings
        rpc_configured = any(item["configured"] for item in self._rpc.summary())
        return [
            IntegrationDescriptor(
                id="etherscan_v2",
                label="Etherscan API V2",
                priority="P0",
                category="audit_ingestion",
                status="configured" if s.etherscan_api_key else "disabled",
                free_mode="Бесплатный API-ключ; один ключ покрывает Ethereum/Base/BSC/Arbitrum через chainid.",
                used_by=["загрузка verified source", "скан по адресу в Mini App", "скан по адресу в web"],
                env_vars=["WR3_ETHERSCAN_API_KEY"],
                next_step="Создать бесплатный Etherscan V2 key, когда нужны реальные сканы verified source.",
                notes=["Без ключа работают вставленный исходный код и ограниченный bytecode-скан."],
            ),
            IntegrationDescriptor(
                id="legacy_explorers",
                label="BaseScan/BscScan/Arbiscan legacy APIs",
                priority="P0",
                category="audit_ingestion",
                status="configured" if any([s.basescan_api_key, s.bscscan_api_key, s.arbiscan_api_key]) else "disabled",
                free_mode="Необязательные бесплатные legacy-ключи как резерв, если Etherscan V2 недоступен.",
                used_by=["резервная загрузка verified source"],
                env_vars=["WR3_BASESCAN_API_KEY", "WR3_BSCSCAN_API_KEY", "WR3_ARBISCAN_API_KEY"],
                next_step="Пропускать, пока V2 не сломается на целевой сети.",
                notes=["Оставлено для совместимости со старым поведением explorer API."],
            ),
            IntegrationDescriptor(
                id="rpc",
                label="RPC API",
                priority="P0",
                category="onchain_reads",
                status="configured" if rpc_configured and not s.public_rpc_fallback_enabled else "free_fallback",
                free_mode="PublicNode без ключа как резерв; RPC URL из env имеет приоритет.",
                used_by=["чтение bytecode/proxy", "будущий fork-mode PoC", "чтение Solana beta"],
                env_vars=[
                    "WR3_ETHEREUM_RPC_URL",
                    "WR3_BASE_RPC_URL",
                    "WR3_BSC_RPC_URL",
                    "WR3_ARBITRUM_RPC_URL",
                    "WR3_SOLANA_RPC_URL",
                ],
                next_step="Для локальной beta использовать PublicNode; Alchemy/Ankr/drpc добавлять только при упоре в rate limit.",
                notes=["Публичный RPC работает best-effort и не считается SLA-уровнем."],
            ),
            IntegrationDescriptor(
                id="openrouter_zdr",
                label="OpenRouter ZDR",
                priority="P0",
                category="llm_triage",
                status="configured" if s.openrouter_api_key and s.llm_provider == "openrouter" else "disabled",
                free_mode="Нет фиксированной месячной оплаты; при выключении используется детерминированный локальный резерв.",
                used_by=["4-agent ИИ-триаж", "граница reasoning для PoC"],
                env_vars=["WR3_LLM_PROVIDER=openrouter", "WR3_OPENROUTER_API_KEY"],
                next_step="Включать только для разрешённых ZDR/local проверок, где приватные findings можно отправлять провайдеру.",
                notes=["Приватные находки и исходники нельзя отправлять non-ZDR провайдерам."],
            ),
            IntegrationDescriptor(
                id="navy_ai",
                label="NavyAI / GPT-5.5",
                priority="P0",
                category="llm_triage",
                status="configured" if s.navy_api_key and s.llm_provider == "navy" else "disabled",
                free_mode="Единый OpenAI-compatible endpoint; конкретная модель может требовать отдельный доступ у провайдера.",
                used_by=["4-agent ИИ-триаж", "security reasoning в локальном/закрытом режиме"],
                env_vars=["WR3_LLM_PROVIDER=navy", "WR3_LLM_MODEL=gpt-5.5", "WR3_NAVY_API_KEY"],
                next_step="Использовать для локальных тестов; перед публичным запуском оставить ZDR/local route для private findings.",
                notes=["ZDR для Navy не подтверждён в документации."],
            ),
            IntegrationDescriptor(
                id="solodit",
                label="Solodit API",
                priority="P0",
                category="rag",
                status="configured" if s.solodit_api_base_url and s.solodit_api_key else "blocked",
                free_mode="Публичный no-key API не подтверждён; локальный RAG-резерв остаётся активным.",
                used_by=["RAG по audit findings", "контекст для триажа"],
                env_vars=["WR3_SOLODIT_API_BASE_URL", "WR3_SOLODIT_API_KEY"],
                next_step="Запросить free/beta Solodit API access или импортировать разрешённые публичные находки вручную.",
                notes=["Не скрейпить copyrighted audit text в публичные отчёты."],
            ),
            IntegrationDescriptor(
                id="telegram",
                label="Telegram Bot API + Mini Apps JS",
                priority="P0",
                category="telegram",
                status="configured" if s.telegram_bot_token else "disabled",
                free_mode="Bot API и Mini Apps JS бесплатны; нужен HTTPS tunnel или домен.",
                used_by=["/scan", "/watch", "/score", "Mini App auth bridge"],
                env_vars=["WR3_TELEGRAM_BOT_TOKEN", "WR3_TELEGRAM_WEBHOOK_SECRET", "WR3_WEB_BASE_URL"],
                next_step="Для тестов использовать текущий Cloudflare tunnel; позже перейти на стабильный домен.",
                notes=["Токен никогда не возвращается этим status endpoint."],
            ),
            IntegrationDescriptor(
                id="defillama_hacks",
                label="DeFiLlama Hacks API",
                priority="P1",
                category="monitoring",
                status="free_fallback",
                free_mode="Публичный endpoint без ключа.",
                used_by=["security news/intelligence", "benchmark context"],
                env_vars=["WR3_DEFILLAMA_HACKS_URL"],
                next_step="Использовать /v1/news/hacks для локального smoke-теста и будущей scheduled ingestion.",
                notes=["Это публичные metadata инцидентов, а не приватные находки."],
            ),
            IntegrationDescriptor(
                id="rsshub",
                label="RSS/RSSHub alerts",
                priority="P1",
                category="monitoring",
                status="configured" if s.rsshub_base_url else "disabled",
                free_mode="Self-hostable/free RSS bridge; публичные инстансы работают best-effort.",
                used_by=["алерты Rekt/SlowMist/PeckShield/CertiK/BlockSec"],
                env_vars=["WR3_RSSHUB_BASE_URL"],
                next_step="Локально оставить выключенным; self-hosted RSSHub добавлять при promotion news worker.",
                notes=["Не отправлять сырые приватные находки в feed processors."],
            ),
            IntegrationDescriptor(
                id="observability",
                label="Sentry + uptime",
                priority="P1",
                category="observability",
                status="configured" if s.sentry_dsn else "disabled",
                free_mode="Sentry free/dev tier или простой health monitor; sensitive scrubber обязателен.",
                used_by=["ошибки API/web", "публичные health checks"],
                env_vars=["WR3_SENTRY_DSN", "WR3_TELEGRAM_ALERT_CHAT_ID"],
                next_step="Включать после review scrubber; /health /live /ready оставить публичными.",
                notes=["Никаких исходников/findings/PoC в Sentry."],
            ),
            IntegrationDescriptor(
                id="solana_data",
                label="Solana RPC / Helius",
                priority="P1/P2",
                category="solana",
                status="configured" if s.solana_rpc_url or s.helius_api_key or s.helius_rpc_url else "free_fallback",
                free_mode="PublicNode Solana RPC fallback; Helius optional.",
                used_by=["чтение программ/accounts в Solana beta"],
                env_vars=["WR3_SOLANA_RPC_URL", "WR3_HELIUS_API_KEY", "WR3_HELIUS_RPC_URL"],
                next_step="Локально использовать public RPC; Helius добавлять только если Solana beta потребует richer data.",
                notes=["Solana остаётся beta в UI/API."],
            ),
            IntegrationDescriptor(
                id="advanced_security_tools",
                label="Forta / Tenderly / BlockSec Phalcon",
                priority="P2",
                category="roadmap",
                status="disabled" if not any([s.forta_api_key, s.tenderly_api_key, s.blocksec_api_key]) else "configured",
                free_mode="Optional/free-tier where available; для localhost MVP не требуется.",
                used_by=["continuous monitoring", "simulation", "post-factum traces"],
                env_vars=["WR3_FORTA_API_KEY", "WR3_TENDERLY_API_KEY", "WR3_BLOCKSEC_API_KEY"],
                next_step="Держать в roadmap, пока не доказано качество core audit.",
                notes=["Никаких активных действий в mainnet вне explicit scope."],
            ),
            IntegrationDescriptor(
                id="resend",
                label="Resend email",
                priority="P2",
                category="notifications",
                status="configured" if s.resend_api_key else "disabled",
                free_mode="Free tier может покрыть малый объём magic links/alerts.",
                used_by=["email auth", "email notifications"],
                env_vars=["WR3_RESEND_API_KEY"],
                next_step="Необязательно, пока beta users не используют email login/alerts.",
                notes=["Текущая локальная авторизация работает без доставки email."],
            ),
        ]
