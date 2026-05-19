from __future__ import annotations

import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from wr3_api.domain.enums import (
    AuditState,
    Chain,
    Exploitability,
    HumanReviewStatus,
    PocStatus,
    RequestedDepth,
    Severity,
    Tier,
    UserIntent,
    Visibility,
)

EVM_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def utc_now() -> datetime:
    return datetime.now(UTC)


class ContractRef(BaseModel):
    address: str | None = None
    name: str = "Unknown"
    file: str | None = None


class SourceLocation(BaseModel):
    file: str | None = None
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)
    function: str | None = None


class Taxonomy(BaseModel):
    swc: str | None = None
    cwe: str | None = None
    wr3_category: str


class Evidence(BaseModel):
    static_trace: str | None = None
    poc_status: PocStatus = PocStatus.NOT_ATTEMPTED
    poc_artifact_uri: str | None = None
    fuzzer_counterexample_uri: str | None = None


class DisclosureAssessment(BaseModel):
    verdict: str = "too_early"
    verdict_label: str = "Рано писать"
    readiness: str = "signal"
    readiness_label: str = "Сигнал"
    can_contact_support: bool = False
    false_positive_risk: str = "high"
    plain_explanation: str = "Это предварительный сигнал. Перед обращением нужна ручная проверка."
    technical_explanation: str = "Детали ещё не рассчитаны."
    next_step: str = "Проверить сигнал вручную и собрать доказательства."
    manual_checklist: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    location_status: str = "unknown"
    location_label: str = "Точное место не определено"


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: f"wr3-find-{uuid4()}")
    audit_id: str
    chain: Chain
    contract: ContractRef
    location: SourceLocation = Field(default_factory=SourceLocation)
    taxonomy: Taxonomy
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    exploitability: Exploitability
    sources: list[str]
    evidence: Evidence = Field(default_factory=Evidence)
    summary: str
    description: str
    impact: str
    recommendation: str
    dismissal_reason: str | None = None
    human_review_status: HumanReviewStatus = HumanReviewStatus.NOT_REQUIRED
    disclosure_assessment: DisclosureAssessment = Field(default_factory=DisclosureAssessment)


class ScoreWeights(BaseModel):
    code_security: float
    centralization: float
    liquidity: float
    team_kyc: float
    behavior: float


class ScoreBreakdown(BaseModel):
    score_version: str
    final_score: int = Field(ge=0, le=100)
    code_security_score: int = Field(ge=0, le=100)
    centralization_score: int = Field(ge=0, le=100)
    liquidity_score: int = Field(ge=0, le=100)
    team_kyc_score: int = Field(ge=0, le=100)
    behavior_score: int = Field(ge=0, le=100)
    caps_applied: list[str]
    weights: ScoreWeights


class ProxyInfo(BaseModel):
    is_proxy: bool = False
    proxy_type: str | None = None
    implementation_address: str | None = None
    admin_address: str | None = None
    owner_hint: str | None = None
    eoa_admin_possible: bool = False
    detection_sources: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class SourceMetadata(BaseModel):
    source_hash: str | None = None
    source_origin: str = "unknown"
    verified_at: datetime | None = None
    explorer_url: str | None = None
    explorer_metadata: dict[str, Any] = Field(default_factory=dict)
    bytecode_only: bool = False
    proxy_info: ProxyInfo = Field(default_factory=ProxyInfo)


class CreateAuditRequest(BaseModel):
    chain: Chain
    address: str | None = None
    source: str | None = None
    allow_bytecode_only: bool = False
    requested_depth: RequestedDepth = RequestedDepth.PRELIMINARY
    visibility: Visibility = Visibility.PRIVATE
    user_intent: UserIntent = UserIntent.PRE_LAUNCH_SELF_CHECK
    tier: Tier = Tier.FREE

    @model_validator(mode="after")
    def require_address_or_source(self) -> "CreateAuditRequest":
        if not self.address and not self.source:
            raise ValueError("нужен адрес или исходный код")
        return self

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return value
        chain = info.data.get("chain")
        if chain != Chain.SOLANA and not EVM_ADDRESS_RE.match(value):
            raise ValueError("EVM-адрес должен начинаться с 0x и содержать 40 hex-символов")
        if chain == Chain.SOLANA and len(value) < 32:
            raise ValueError("Solana-адрес слишком короткий")
        return value


class CreateAuditResponse(BaseModel):
    audit_id: UUID
    state: AuditState
    status_url: str
    estimated_wait_seconds: int
    limitations: list[str]
    owner_access_token: str
    public_report_token: str | None = None


class ScoutTarget(BaseModel):
    source: str = "defillama_protocols"
    protocol_name: str
    slug: str
    category: str | None = None
    chain: Chain
    address: str
    tvl_usd: float | None = None
    official_url: str | None = None
    twitter_url: str | None = None
    security_txt_url: str | None = None
    security_email_guess: str | None = None
    contact_instructions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ScoutRunRequest(BaseModel):
    source: str = "defillama_protocols"
    limit: int = Field(default=5, ge=1, le=25)
    min_tvl_usd: float = Field(default=0, ge=0)
    chains: list[Chain] = Field(default_factory=list)
    dry_run: bool = False
    requested_depth: RequestedDepth = RequestedDepth.PRELIMINARY
    tier: Tier = Tier.FREE


class ScoutRunAllRequest(BaseModel):
    source: str = "defillama_protocols"
    per_chain_limit: int = Field(default=3, ge=1, le=10)
    min_tvl_usd: float = Field(default=0, ge=0)
    chains: list[Chain] = Field(default_factory=list)
    dry_run: bool = False
    requested_depth: RequestedDepth = RequestedDepth.DEEP
    tier: Tier = Tier.TEAM


class ScoutQueuedAudit(BaseModel):
    audit_id: UUID
    owner_access_token: str
    chain: Chain
    address: str
    protocol_name: str
    status_url: str
    report_url: str
    limitations: list[str] = Field(default_factory=list)


class ScoutRunResult(BaseModel):
    source: str
    discovered_count: int
    queued_count: int
    skipped_count: int
    targets: list[ScoutTarget]
    audits: list[ScoutQueuedAudit]
    limitations: list[str] = Field(default_factory=list)


class ScoutReviewItem(BaseModel):
    bucket: str
    action_label: str
    audit_id: UUID
    owner_access_token: str | None = None
    chain: Chain
    address: str | None = None
    state: AuditState
    score: int | None = None
    finding_count: int = 0
    highest_severity: Severity | None = None
    primary_title: str | None = None
    verdict_label: str
    readiness_label: str
    can_contact_support: bool = False
    why: str
    next_step: str
    evidence_gaps: list[str] = Field(default_factory=list)
    support_route: list[str] = Field(default_factory=list)
    report_url: str


class ScoutReviewQueue(BaseModel):
    ready_to_write: list[ScoutReviewItem] = Field(default_factory=list)
    needs_validation: list[ScoutReviewItem] = Field(default_factory=list)
    skip: list[ScoutReviewItem] = Field(default_factory=list)
    totals: dict[str, int] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class AuditAccessSummary(BaseModel):
    is_owner: bool = False
    is_public_view: bool = False
    can_view_private_findings: bool = False
    can_view_raw_outputs: bool = False
    auth_provider: str | None = None


class SecurityAgentSummary(BaseModel):
    provider: str = "disabled"
    model: str = "local-deterministic-triage"
    status: str = "not_started"
    status_label: str = "ИИ-агент ещё не запускался"
    provider_invoked: bool = False
    fallback: str = "not_started"
    error_type: str | None = None
    agent_roles: list[str] = Field(default_factory=list)
    agent_payloads_received: list[str] = Field(default_factory=list)
    zdr_required: bool = True
    prompt_wrapped_untrusted_source: bool = False
    explanation: str = (
        "Пока findings создают статические инструменты и локальные эвристики. "
        "ИИ-агент должен только триажить и снижать false positives."
    )
    recommendation: str = (
        "Для глубокого режима подключи платную ZDR/local модель в WR3_LLM_MODEL. "
        "Free-модели могут упираться в rate-limit и уходить в fallback."
    )


class AuditEvent(BaseModel):
    audit_id: UUID
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class EngineRunSummary(BaseModel):
    audit_id: UUID
    engine: str
    status: str
    duration_ms: int
    artifact_uri: str | None = None
    error: str | None = None


class AuditSummary(BaseModel):
    audit_id: UUID
    state: AuditState
    chain: Chain
    address: str | None
    tier: Tier
    progress: int = Field(ge=0, le=100)
    score: ScoreBreakdown | None = None
    limitations: list[str]
    failed_stages: list[str]
    engine_version: str
    score_version: str
    static_analysis_status: str = "not_started"
    security_agent: SecurityAgentSummary = Field(default_factory=SecurityAgentSummary)
    source_metadata: SourceMetadata = Field(default_factory=SourceMetadata)
    retention_until: datetime | None = None
    adversarial_input_detected: bool = False
    access: AuditAccessSummary = Field(default_factory=AuditAccessSummary)


class AuditRecord(BaseModel):
    audit_id: UUID = Field(default_factory=uuid4)
    user_id: str | None = None
    owner_access_token: str = Field(default_factory=lambda: secrets.token_urlsafe(24))
    public_report_token: str | None = None
    request: CreateAuditRequest
    state: AuditState = AuditState.CREATED
    findings: list[Finding] = Field(default_factory=list)
    score: ScoreBreakdown | None = None
    limitations: list[str] = Field(default_factory=list)
    failed_stages: list[str] = Field(default_factory=list)
    events: list[AuditEvent] = Field(default_factory=list)
    engine_runs: list[EngineRunSummary] = Field(default_factory=list)
    source_metadata: SourceMetadata = Field(default_factory=SourceMetadata)
    engine_version: str = "wr3-engine-v0.1"
    score_version: str = "wr3-score-v0.1"
    adversarial_input_detected: bool = False
    retention_until: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def to_summary(
        self,
        progress: int,
        access: AuditAccessSummary | None = None,
    ) -> AuditSummary:
        return AuditSummary(
            audit_id=self.audit_id,
            state=self.state,
            chain=self.request.chain,
            address=self.request.address,
            tier=self.request.tier,
            progress=progress,
            score=self.score,
            limitations=self.limitations,
            failed_stages=self.failed_stages,
            engine_version=self.engine_version,
            score_version=self.score_version,
            static_analysis_status=self._static_analysis_status(),
            security_agent=self._security_agent_summary(),
            source_metadata=self.source_metadata,
            retention_until=self.retention_until,
            adversarial_input_detected=self.adversarial_input_detected,
            access=access or AuditAccessSummary(),
        )

    def _static_analysis_status(self) -> str:
        static_runs = [run for run in self.engine_runs if run.engine in {"aderyn", "wake", "slither", "wr3_heuristic_evm", "wr3_heuristic_solana"}]
        if not static_runs:
            return "not_started"
        successes = [run for run in static_runs if run.status == "success"]
        failures = [run for run in static_runs if run.status == "failed"]
        if successes and failures:
            return "partial"
        if successes:
            return "success"
        if failures:
            return "failed"
        return "skipped"

    def _security_agent_summary(self) -> SecurityAgentSummary:
        route_events = [event for event in self.events if event.event_type == "llm_triage_route"]
        if not route_events:
            return SecurityAgentSummary()
        payload = route_events[-1].payload
        fallback = str(payload.get("fallback") or "unknown")
        provider_invoked = bool(payload.get("provider_invoked"))
        received = payload.get("agent_payloads_received")
        agent_payloads_received = [str(item) for item in received] if isinstance(received, list) else []
        provider = str(payload.get("provider") or "unknown")
        model = str(payload.get("model") or "unknown")
        error_type = payload.get("error_type")
        error_text = str(error_type) if error_type else None
        if not provider_invoked:
            status = "disabled"
            status_label = "ИИ-агент не запускался"
            explanation = (
                "В этом прогоне findings нашли статические инструменты/эвристики. "
                "LLM не участвовал в проверке."
            )
        elif fallback == "deterministic" or error_type:
            status = "fallback"
            status_label = "ИИ-агент не подтвердил"
            if provider == "navy" and model == "claude-opus-4.7" and error_text == "HTTPStatusError:403":
                explanation = (
                    "wr3 выбрал Claude Opus 4.7 через NavyAI, но Navy вернул отказ доступа. "
                    "Эта модель требует paid/Max доступ в аккаунте NavyAI, поэтому ИИ-проверка не была выполнена."
                )
            elif error_text == "HTTPStatusError:429":
                explanation = (
                    f"Была выбрана модель {model} через {provider}, но провайдер вернул rate limit. "
                    "wr3 не считает это ИИ-подтверждением и показывает сигнал как кандидата."
                )
            else:
                explanation = (
                    f"Была выбрана модель {model} через {provider}, но провайдер не дал полноценную проверку. "
                    "wr3 не считает это ИИ-подтверждением и показывает сигнал как кандидата."
                )
        elif agent_payloads_received:
            status = "provider_confirmed"
            status_label = "ИИ-агент отработал"
            explanation = (
                f"Модель {model} через {provider} вернула ответы triage-агентов. "
                "Это усиливает сигнал, но не заменяет PoC и ручную проверку."
            )
        else:
            status = "unknown"
            status_label = "Статус ИИ-агента неясен"
            explanation = "wr3 не получил достаточно данных, чтобы считать AI-triage успешным."

        roles = payload.get("agent_roles")
        return SecurityAgentSummary(
            provider=provider,
            model=model,
            status=status,
            status_label=status_label,
            provider_invoked=provider_invoked,
            fallback=fallback,
            error_type=error_text,
            agent_roles=[str(item) for item in roles] if isinstance(roles, list) else [],
            agent_payloads_received=agent_payloads_received,
            zdr_required=bool(payload.get("zdr_required", True)),
            prompt_wrapped_untrusted_source=bool(payload.get("prompt_wrapped_untrusted_source")),
            explanation=explanation,
        )


class PublicProjectSummary(BaseModel):
    chain: Chain
    address: str
    score: ScoreBreakdown | None = None
    safe_harbor_status: bool = False
    public_findings: list[Finding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class DisclosureCaseRequest(BaseModel):
    finding_id: str
    project_contact: str
    scope_note: str


class FindingReviewRequest(BaseModel):
    status: HumanReviewStatus
    note: str | None = None

    @field_validator("status")
    @classmethod
    def require_terminal_review_status(cls, value: HumanReviewStatus) -> HumanReviewStatus:
        if value not in {HumanReviewStatus.APPROVED, HumanReviewStatus.REJECTED}:
            raise ValueError("review status must be approved or rejected")
        return value


class DisclosureContactLogRequest(BaseModel):
    channel: str
    message: str


class DisclosureAdvanceRequest(BaseModel):
    status: str
    note: str | None = None


class DisclosureCase(BaseModel):
    id: str = Field(default_factory=lambda: f"wr3-disclosure-{uuid4()}")
    finding_id: str
    status: str = "private_contact_pending"
    contact_log: list[str] = Field(default_factory=list)
    deadline_next: datetime = Field(default_factory=lambda: utc_now() + timedelta(days=7))
    created_at: datetime = Field(default_factory=utc_now)


class SiweNonceRequest(BaseModel):
    address: str
    chain: Chain = Chain.ETHEREUM

    @field_validator("address")
    @classmethod
    def validate_evm_address(cls, value: str) -> str:
        if not EVM_ADDRESS_RE.match(value):
            raise ValueError("SIWE address must be 0x-prefixed and 40 hex chars")
        return value


class SiweNonceResponse(BaseModel):
    nonce: str
    message: str
    expires_at: datetime


class SiweVerifyRequest(BaseModel):
    address: str
    nonce: str
    message: str
    signature: str


class EmailLoginRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not EMAIL_RE.match(value):
            raise ValueError("valid email is required")
        return value.lower()


class EmailMagicLinkRequest(EmailLoginRequest):
    pass


class EmailMagicLinkResponse(BaseModel):
    email: str
    delivery_enabled: bool
    magic_link_url: str | None = None
    dev_verify_token: str | None = None
    expires_at: datetime
    limitations: list[str] = Field(default_factory=list)


class EmailMagicLinkVerifyRequest(BaseModel):
    email: str
    token: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not EMAIL_RE.match(value):
            raise ValueError("valid email is required")
        return value.lower()


class TelegramInitDataRequest(BaseModel):
    init_data: str
    explicit_account_consent: bool = False


class AuthSessionResponse(BaseModel):
    user_id: str
    provider: str
    subject: str
    bearer_token: str
    expires_at: datetime
    limitations: list[str] = Field(default_factory=list)


class BillingPlan(BaseModel):
    tier: Tier
    name: str
    price_usd_month: int
    scan_quota: str
    retention_days: int
    poc_access: bool
    notes: list[str] = Field(default_factory=list)


class OneShotAuditPackage(BaseModel):
    id: str
    name: str
    price_usd_min: int
    price_usd_max: int
    sla_hours_min: int
    sla_hours_max: int
    includes: list[str]
    limitations: list[str] = Field(default_factory=list)


class ManualPaymentIntentRequest(BaseModel):
    tier: Tier


class CheckoutIntentRequest(BaseModel):
    tier: Tier
    provider: str = "polar"

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        allowed = {"polar", "request_finance"}
        if value not in allowed:
            raise ValueError(f"provider must be one of {sorted(allowed)}")
        return value


class CheckoutIntent(BaseModel):
    id: str = Field(default_factory=lambda: f"wr3-checkout-{uuid4()}")
    user_id: str
    tier: Tier
    amount_usd: int
    provider: str
    checkout_url: str | None = None
    status: str = "requires_provider_configuration"
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(default_factory=lambda: utc_now() + timedelta(hours=24))
    limitations: list[str] = Field(default_factory=list)


class ManualPaymentIntent(BaseModel):
    id: str = Field(default_factory=lambda: f"wr3-pay-{uuid4()}")
    user_id: str
    tier: Tier
    amount_usd: int
    provider: str = "manual_usdc"
    accepted_networks: list[str] = Field(default_factory=lambda: ["base", "arbitrum"])
    payment_address: str
    memo: str
    status: str = "pending_manual_review"
    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(default_factory=lambda: utc_now() + timedelta(hours=24))
    limitations: list[str] = Field(default_factory=list)


class ConfirmSubscriptionRequest(BaseModel):
    user_id: str
    tier: Tier
    provider: str = "manual_usdc"
    tx_reference: str


class SubscriptionRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"wr3-sub-{uuid4()}")
    user_id: str
    tier: Tier
    provider: str
    status: str = "active"
    tx_reference: str | None = None
    quota_used: int = 0
    current_period_end: datetime = Field(default_factory=lambda: utc_now() + timedelta(days=30))
    created_at: datetime = Field(default_factory=utc_now)


class WatchlistRequest(BaseModel):
    chain: Chain
    address: str
    label: str | None = None
    alert_channels: list[str] = Field(default_factory=lambda: ["telegram"])


class WatchlistEntry(BaseModel):
    id: str = Field(default_factory=lambda: f"wr3-watch-{uuid4()}")
    user_id: str
    chain: Chain
    address: str
    label: str | None = None
    alert_channels: list[str]
    status: str = "active"
    created_at: datetime = Field(default_factory=utc_now)
    limitations: list[str] = Field(default_factory=list)


class WebhookTestRequest(BaseModel):
    url: str
    event_type: str = "wr3.test"

    @field_validator("url")
    @classmethod
    def validate_webhook_url(cls, value: str) -> str:
        if not (value.startswith("https://") or value.startswith("http://127.0.0.1") or value.startswith("http://localhost")):
            raise ValueError("webhook URL must be https or localhost for MVP tests")
        return value


class WebhookTestResponse(BaseModel):
    delivered: bool
    event_type: str
    payload_preview: dict[str, Any] = Field(default_factory=dict)
    signature: str | None = None
    limitations: list[str] = Field(default_factory=list)
