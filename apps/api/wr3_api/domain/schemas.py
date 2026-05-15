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


class AuditAccessSummary(BaseModel):
    is_owner: bool = False
    is_public_view: bool = False
    can_view_private_findings: bool = False
    can_view_raw_outputs: bool = False
    auth_provider: str | None = None


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
            source_metadata=self.source_metadata,
            retention_until=self.retention_until,
            adversarial_input_detected=self.adversarial_input_detected,
            access=access or AuditAccessSummary(),
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
