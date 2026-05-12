from enum import StrEnum


class Chain(StrEnum):
    ETHEREUM = "ethereum"
    BASE = "base"
    BSC = "bsc"
    ARBITRUM = "arbitrum"
    SOLANA = "solana"


class AuditState(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    INGESTING = "ingesting"
    NEEDS_SOURCE = "needs_source"
    STATIC_RUNNING = "static_running"
    TRIAGE_RUNNING = "triage_running"
    POC_RUNNING = "poc_running"
    FUZZING_RUNNING = "fuzzing_running"
    SCORING = "scoring"
    HUMAN_REVIEW = "human_review"
    CHANGES_REQUESTED = "changes_requested"
    PARTIAL = "partial"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    REJECTED = "rejected"
    TERMINAL = "terminal"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Exploitability(StrEnum):
    CONFIRMED = "confirmed"
    LIKELY = "likely"
    THEORETICAL = "theoretical"
    UNKNOWN = "unknown"
    DISMISSED = "dismissed"


class PocStatus(StrEnum):
    NOT_ATTEMPTED = "not_attempted"
    FAILED = "failed"
    CONFIRMED = "confirmed"


class HumanReviewStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Tier(StrEnum):
    FREE = "free"
    HOBBY = "hobby"
    TEAM = "team"
    PRO = "pro"


class RequestedDepth(StrEnum):
    PRELIMINARY = "preliminary"
    STANDARD = "standard"
    DEEP = "deep"


class Visibility(StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"


class UserIntent(StrEnum):
    PRE_LAUNCH_SELF_CHECK = "pre_launch_self_check"
    THIRD_PARTY_RESEARCH = "third_party_research"
    MONITORING = "monitoring"
