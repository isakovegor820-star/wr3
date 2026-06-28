from __future__ import annotations

import asyncio
from datetime import timedelta
from hmac import compare_digest
from uuid import UUID

from wr3_api.adapters.base import EngineAdapter, EngineRunOptions, EngineRunResult, NormalizedSource
from wr3_api.adapters.registry import default_adapters
from wr3_api.core.config import get_settings
from wr3_api.domain.enums import AuditState, Chain, Exploitability, PocStatus, Severity, UserIntent
from wr3_api.domain.safety import (
    detect_prompt_injection,
    redact_findings_for_public,
    validate_request_safety,
)
from wr3_api.domain.schemas import (
    AuditEvent,
    AuditAccessSummary,
    AuditRecord,
    AuditSummary,
    DisclosureAssessment,
    DisclosureAdvanceRequest,
    CreateAuditRequest,
    DisclosureContactLogRequest,
    DisclosureCase,
    DisclosureCaseRequest,
    DisclosureManualSentRequest,
    DisclosurePacketActionRequest,
    DisclosurePacketRequest,
    DisclosurePacketResponse,
    EngineRunSummary,
    Evidence,
    ContractRef,
    Finding,
    FindingReviewRequest,
    PublicProjectSummary,
    Taxonomy,
    utc_now,
)
from wr3_api.domain.scoring import ScoreContext, score_audit
from wr3_api.domain.state_machine import STAGE_PROGRESS, assert_transition, can_transition
from wr3_api.services.auth import AuditAccessContext, AuthContext
from wr3_api.services.contracts import build_source_metadata
from wr3_api.services.explorers import ExplorerSourcePuller, default_explorer_pullers
from wr3_api.services.fuzzing import FuzzingWorker, FuzzWorkerResult
from wr3_api.services.llm_triage import LlmTriageRouter
from wr3_api.services.notifications import NotificationService
from wr3_api.services.poc import (
    FoundryPocWorker,
    ensure_solidity_pragma,
    extract_primary_contract,
    high_risk_poc_candidates,
)
from wr3_api.services.quota import InMemoryQuotaLimiter
from wr3_api.services.repository import (
    AuditRepository,
    DisclosureRepository,
    build_audit_repository,
    build_disclosure_repository,
)
from wr3_api.services.report_renderer import ReportRenderer
from wr3_api.services.retention import RetentionRunResult, RetentionService
from wr3_api.services.safe_harbor import SafeHarborRegistry
from wr3_api.services.triage_agents import TriageConsensus
from wr3_api.services.artifacts import ArtifactEncryptionRequired, ArtifactVault


class AuditNotFound(KeyError):
    pass


class AuditAccessDenied(PermissionError):
    pass


DISCLOSURE_DEADLINE_DAYS: dict[str, int] = {
    "private_contact_pending": 7,
    "seal_911_escalation": 14,
    "cve_euvd_notice": 45,
    "limited_disclosure_allowed": 90,
    "full_disclosure_allowed": 180,
    "resolved": 0,
    "closed": 0,
}

OFFICIAL_CONTACT_SOURCES = {
    "bug_bounty_portal",
    "security_txt",
    "github_security_policy",
    "security_md",
    "official_website_email",
    "official_website_contact_form",
}


class AuditService:
    def __init__(
        self,
        adapters: list[EngineAdapter] | None = None,
        explorers: list[ExplorerSourcePuller] | None = None,
        audit_repository: AuditRepository | None = None,
        disclosure_repository: DisclosureRepository | None = None,
        safe_harbor_registry: SafeHarborRegistry | None = None,
    ) -> None:
        settings = get_settings()
        self._settings = settings
        self._adapters = adapters or default_adapters()
        self._explorers = explorers or default_explorer_pullers()
        self._audit_repository = audit_repository or build_audit_repository(settings.database_url)
        self._disclosure_repository = disclosure_repository or build_disclosure_repository(settings.database_url)
        self._quota = InMemoryQuotaLimiter()
        self._renderer = ReportRenderer()
        self._poc_worker = FoundryPocWorker()
        self._fuzz_worker = FuzzingWorker()
        self._llm_triage = LlmTriageRouter()
        self._triage_consensus = TriageConsensus()
        self._safe_harbor = safe_harbor_registry or SafeHarborRegistry()
        self._artifact_vault = ArtifactVault()
        self._notifications = NotificationService()

    async def create_audit(self, request: CreateAuditRequest, actor: AuthContext | None = None) -> AuditRecord:
        record = AuditRecord(request=request, user_id=actor.user_id if actor else None)
        if request.source and len(request.source.encode("utf-8")) > self._settings.max_source_bytes:
            record.limitations.append("source_exceeds_max_source_bytes")
            self._audit_repository.save(record)
            self._transition(record, AuditState.REJECTED, reason="source_too_large")
            return record
        record.limitations.extend(validate_request_safety(request))
        quota = self._quota.check(
            user_key=record.user_id or request.address or "anonymous-source",
            tier=request.tier,
            requested_depth=request.requested_depth,
        )
        record.limitations.extend(quota.limitations)
        record.request.requested_depth = quota.effective_depth
        record.retention_until = record.created_at + timedelta(days=quota.retention_days)
        if actor is None or not actor.is_authenticated:
            record.limitations.append("anonymous_owner_token_required_for_private_access")
        record.adversarial_input_detected = detect_prompt_injection(request.source)
        if record.adversarial_input_detected:
            record.limitations.append("adversarial_input_detected")
        self._audit_repository.save(record)

        self._transition(record, AuditState.QUEUED, reason="audit_created")
        return record

    async def process_audit(self, audit_id: UUID) -> None:
        record = self.get_record(audit_id)
        if record.state != AuditState.QUEUED:
            record.events.append(
                AuditEvent(
                    audit_id=record.audit_id,
                    event_type="processor_ignored",
                    payload={"state": record.state, "reason": "job_not_queued"},
                )
            )
            self._audit_repository.save(record)
            return
        try:
            await self._process_record(record)
        except Exception as exc:  # pragma: no cover - defensive safety net
            record.failed_stages.append("processor:unhandled_exception")
            record.limitations.append("audit_processing_failed_internal_error")
            record.events.append(
                AuditEvent(
                    audit_id=record.audit_id,
                    event_type="processor_failed",
                    payload={"error_type": exc.__class__.__name__},
                )
            )
            if can_transition(record.state, AuditState.FAILED):
                self._transition(record, AuditState.FAILED, reason="processor_failed")
            else:
                self._audit_repository.save(record)

    def get_record(self, audit_id: UUID) -> AuditRecord:
        try:
            record = self._audit_repository.get(audit_id)
        except KeyError as exc:
            raise AuditNotFound(str(audit_id)) from exc
        if record is None:
            raise AuditNotFound(str(audit_id))
        return record

    def save_record(self, record: AuditRecord) -> None:
        self._audit_repository.save(record)

    def find_recent_monitoring_audit(
        self,
        *,
        chain: Chain,
        address: str,
        window_hours: int,
    ) -> AuditRecord | None:
        cutoff = utc_now() - timedelta(hours=window_hours)
        normalized_address = address.lower()
        for record in sorted(self._audit_repository.list_records(), key=lambda item: item.updated_at, reverse=True):
            if record.updated_at < cutoff:
                continue
            if record.request.user_intent != UserIntent.MONITORING:
                continue
            if record.request.chain != chain:
                continue
            if (record.request.address or "").lower() != normalized_address:
                continue
            return record
        return None

    def list_audits_for_dashboard(
        self,
        *,
        chain: Chain | None = None,
        state: AuditState | None = None,
        severity: Severity | None = None,
        actor: AuthContext | None = None,
    ) -> list[dict[str, object]]:
        is_local_dashboard = self._settings.environment == "development"
        if not is_local_dashboard and (actor is None or not actor.is_reviewer):
            raise AuditAccessDenied("reviewer_access_required_for_audit_dashboard")

        rows: list[dict[str, object]] = []
        for record in sorted(self._audit_repository.list_records(), key=lambda item: item.updated_at, reverse=True):
            if chain and record.request.chain != chain:
                continue
            if state and record.state != state:
                continue
            highest_severity = self._highest_severity(record.findings)
            if severity and highest_severity != severity:
                continue
            rows.append(
                self._dashboard_row(record, highest_severity, is_local_dashboard)
            )
        return rows

    def _dashboard_row(
        self,
        record: AuditRecord,
        highest_severity: Severity | None,
        is_local_dashboard: bool,
    ) -> dict[str, object]:
        primary = self._primary_finding(record)
        assessment = primary.disclosure_assessment if primary else None
        return {
            "audit_id": str(record.audit_id),
            "owner_access_token": record.owner_access_token if is_local_dashboard else None,
            "chain": record.request.chain,
            "address": record.request.address,
            "state": record.state,
            "tier": record.request.tier,
            "requested_depth": record.request.requested_depth,
            "score": record.score.model_dump(mode="json") if record.score else None,
            "finding_count": len(record.findings),
            "highest_severity": highest_severity,
            "limitations_count": len(record.limitations),
            "project_key": f"{record.request.chain}:{record.request.address or 'source-only'}",
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "static_analysis_status": record._static_analysis_status(),
            "primary_finding_id": primary.id if primary else None,
            "primary_finding_title": primary.summary if primary else None,
            "primary_verdict": assessment.verdict if assessment else "no_signal",
            "primary_verdict_label": assessment.verdict_label if assessment else "Нет сигнала",
            "primary_readiness": assessment.readiness if assessment else "no_signal",
            "primary_readiness_label": assessment.readiness_label if assessment else "Нет сигнала",
            "primary_next_step": assessment.next_step if assessment else "Запустить или дождаться скана.",
            "primary_explanation": assessment.plain_explanation if assessment else "Находок пока нет.",
            "primary_false_positive_risk": assessment.false_positive_risk if assessment else "unknown",
            "primary_evidence_gaps": assessment.evidence_gaps if assessment else [],
            "can_create_disclosure": bool(assessment.can_contact_support) if assessment else False,
        }

    def _primary_finding(self, record: AuditRecord) -> Finding | None:
        if not record.findings:
            return None
        severity_rank = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        return sorted(record.findings, key=lambda item: (severity_rank[item.severity], -item.confidence))[0]

    def get_summary(self, audit_id: UUID, access: AuditAccessContext | None = None) -> AuditSummary:
        record = self.get_record(audit_id)
        access_summary = self._access_summary(record, access)
        if not access_summary.is_owner and not access_summary.is_public_view:
            raise AuditAccessDenied("private_audit_requires_owner_or_public_token")
        return record.to_summary(progress=STAGE_PROGRESS[record.state], access=access_summary)

    def get_events(self, audit_id: UUID, access: AuditAccessContext | None = None) -> list[AuditEvent]:
        record = self.get_record(audit_id)
        self._ensure_owner(record, access)
        return record.events

    def get_findings(
        self,
        audit_id: UUID,
        *,
        public: bool = False,
        access: AuditAccessContext | None = None,
    ) -> list[Finding]:
        record = self.get_record(audit_id)
        if public:
            return redact_findings_for_public(record.findings)
        self._ensure_owner(record, access)
        return record.findings

    def render_report(
        self,
        audit_id: UUID,
        *,
        fmt: str = "markdown",
        access: AuditAccessContext | None = None,
    ) -> str:
        record = self.get_record(audit_id)
        self._ensure_owner_or_report_token(record, access)
        if fmt == "html":
            return self._renderer.render_html(record)
        return self._renderer.render_markdown(record)

    def raw_outputs_metadata(self, audit_id: UUID, access: AuditAccessContext | None = None) -> dict[str, object]:
        record = self.get_record(audit_id)
        self._ensure_owner(record, access)
        return {
            "audit_id": str(record.audit_id),
            "gated": False,
            "reason": "owner_verified_private_artifact_access",
            "owner_verified": True,
            "engines": [
                {
                    "engine": run.engine,
                    "status": run.status,
                    "duration_ms": run.duration_ms,
                    "artifact_uri": run.artifact_uri,
                    "error": run.error,
                }
                for run in record.engine_runs
            ],
        }

    def review_finding(
        self,
        audit_id: UUID,
        finding_id: str,
        request: FindingReviewRequest,
        actor: AuthContext | None = None,
    ) -> Finding:
        if actor is None or not actor.is_reviewer:
            raise AuditAccessDenied("reviewer_access_required_for_finding_review")
        record = self.get_record(audit_id)
        for index, finding in enumerate(record.findings):
            if finding.id != finding_id:
                continue
            updated = finding.model_copy(update={"human_review_status": request.status})
            record.findings[index] = updated
            record.events.append(
                AuditEvent(
                    audit_id=record.audit_id,
                    event_type="finding_reviewed",
                    payload={
                        "finding_id": finding_id,
                        "status": request.status,
                        "note": request.note,
                    },
                )
            )
            self._audit_repository.save(record)
            return updated
        raise AuditNotFound(finding_id)

    def create_disclosure_case(
        self,
        request: DisclosureCaseRequest,
        actor: AuthContext | None = None,
    ) -> DisclosureCase:
        if actor is None or not actor.is_reviewer:
            raise AuditAccessDenied("reviewer_access_required_for_disclosure_case")
        case = DisclosureCase(
            finding_id=request.finding_id,
            project_contact=request.project_contact,
            scope_note=request.scope_note,
            contact_log=[
                "Day 0: private responsible disclosure case opened.",
                f"Contact target captured: {request.project_contact}",
                f"Scope note: {request.scope_note}",
            ],
        )
        self._disclosure_repository.save(case)
        return case

    def get_disclosure_case(self, case_id: str, actor: AuthContext | None = None) -> DisclosureCase:
        if actor is None or not actor.is_reviewer:
            raise AuditAccessDenied("reviewer_access_required_for_disclosure_case")
        case = self._disclosure_repository.get(case_id)
        if case is None:
            raise AuditNotFound(case_id)
        return case

    def list_disclosure_cases(self, actor: AuthContext | None = None) -> list[DisclosureCase]:
        if actor is None or not actor.is_reviewer:
            raise AuditAccessDenied("reviewer_access_required_for_disclosure_case")
        return self._disclosure_repository.list_cases()

    def get_disclosure_packet(self, case_id: str, actor: AuthContext | None = None) -> DisclosurePacketResponse:
        case = self.get_disclosure_case(case_id, actor)
        return self._packet_response(case)

    def prepare_disclosure_packet(
        self,
        request: DisclosurePacketRequest,
        actor: AuthContext | None = None,
    ) -> DisclosurePacketResponse:
        if actor is None or not actor.is_reviewer:
            raise AuditAccessDenied("reviewer_access_required_for_disclosure_packet")
        record = self.get_record(request.audit_id)
        finding = self._finding_for_packet(record, request.finding_id)
        existing = next(
            (case for case in self._disclosure_repository.list_cases() if case.finding_id == finding.id),
            None,
        )
        case = existing or DisclosureCase(finding_id=finding.id)
        case.audit_id = record.audit_id
        case.project_name = request.project_name or case.project_name or finding.contract.name
        case.project_contact = request.official_contact
        case.contact_source = request.contact_source
        case.scope_note = request.scope_note
        case.web_url = f"{self._settings.web_base_url}/audits/{record.audit_id}?owner_token={record.owner_access_token}"
        case.internal_pdf_url = f"/v1/disclosure-cases/{case.id}/reports/internal.pdf"
        case.external_pdf_url = f"/v1/disclosure-cases/{case.id}/reports/external.pdf"
        case.internal_report_markdown = self._renderer.render_internal_disclosure_markdown(record, finding, case)
        case.external_report_markdown = self._renderer.render_external_disclosure_markdown(record, finding, case)
        case.draft_message = self._safe_disclosure_draft(record, finding, case)
        case.pdfs_generated = True
        case.candidate_detected = True
        case.confirmed_by_poc = self._is_confirmed_by_poc_or_fork(finding)
        case.approved_to_contact = False
        case.manually_sent = False
        case.dismissed = False
        case.limitations = self._packet_limitations(record, finding, case)
        case.needs_human_approval = (
            case.confirmed_by_poc
            and self._has_clear_impact(finding)
            and self._official_contact_allowed(case.contact_source)
        )
        if case.needs_human_approval:
            case.readiness_state = "needs_human_approval"
        elif case.confirmed_by_poc:
            case.readiness_state = "pdfs_generated"
        else:
            case.readiness_state = "candidate_detected"
        case.status = case.readiness_state
        case.contact_log.append(
            f"{utc_now().date().isoformat()} [packet]: disclosure packet prepared; state={case.readiness_state}"
        )
        case.contact_log.append(
            f"{utc_now().date().isoformat()} [draft]: safe draft generated; no external message sent"
        )
        self._disclosure_repository.save(case)
        return self._packet_response(case, record=record, finding=finding)

    def append_disclosure_contact(
        self,
        case_id: str,
        request: DisclosureContactLogRequest,
        actor: AuthContext | None = None,
    ) -> DisclosureCase:
        case = self.get_disclosure_case(case_id, actor)
        case.contact_log.append(f"{utc_now().date().isoformat()} [{request.channel}]: {request.message}")
        self._disclosure_repository.save(case)
        return case

    def approve_disclosure_packet(
        self,
        case_id: str,
        request: DisclosurePacketActionRequest,
        actor: AuthContext | None = None,
    ) -> DisclosurePacketResponse:
        case = self.get_disclosure_case(case_id, actor)
        if not case.needs_human_approval:
            raise ValueError("disclosure_packet_not_ready_for_approval")
        case.needs_human_approval = False
        case.approved_to_contact = True
        case.readiness_state = "approved_to_contact"
        case.status = "approved_to_contact"
        if request.note:
            case.contact_log.append(f"{utc_now().date().isoformat()} [approve-note]: {request.note}")
        case.contact_log.append(f"{utc_now().date().isoformat()} [approve]: human approved manual contact")
        self._disclosure_repository.save(case)
        return self._packet_response(case)

    def mark_disclosure_manually_sent(
        self,
        case_id: str,
        request: DisclosureManualSentRequest,
        actor: AuthContext | None = None,
    ) -> DisclosurePacketResponse:
        case = self.get_disclosure_case(case_id, actor)
        if not case.approved_to_contact:
            raise ValueError("disclosure_packet_requires_approval_before_manual_send")
        case.manually_sent = True
        case.readiness_state = "manually_sent"
        case.status = "manually_sent"
        case.contact_log.append(
            f"{utc_now().date().isoformat()} [{request.channel}]: manual send logged; wr3 did not auto-send"
        )
        if request.note:
            case.contact_log.append(f"{utc_now().date().isoformat()} [manual-send-note]: {request.note}")
        self._disclosure_repository.save(case)
        return self._packet_response(case)

    def request_more_disclosure_review(
        self,
        case_id: str,
        request: DisclosurePacketActionRequest,
        actor: AuthContext | None = None,
    ) -> DisclosurePacketResponse:
        case = self.get_disclosure_case(case_id, actor)
        case.needs_human_approval = False
        case.approved_to_contact = False
        case.readiness_state = "confirmed_by_poc" if case.confirmed_by_poc else "candidate_detected"
        case.status = "needs_more_review"
        if request.note:
            case.contact_log.append(f"{utc_now().date().isoformat()} [needs-review]: {request.note}")
        self._disclosure_repository.save(case)
        return self._packet_response(case)

    def dismiss_disclosure_packet(
        self,
        case_id: str,
        request: DisclosurePacketActionRequest,
        actor: AuthContext | None = None,
    ) -> DisclosurePacketResponse:
        case = self.get_disclosure_case(case_id, actor)
        case.dismissed = True
        case.needs_human_approval = False
        case.approved_to_contact = False
        case.readiness_state = "dismissed"
        case.status = "dismissed"
        if request.note:
            case.contact_log.append(f"{utc_now().date().isoformat()} [dismiss]: {request.note}")
        self._disclosure_repository.save(case)
        return self._packet_response(case)

    def render_disclosure_pdf(self, case_id: str, variant: str, actor: AuthContext | None = None) -> bytes:
        case = self.get_disclosure_case(case_id, actor)
        if variant == "internal":
            title = "wr3 internal disclosure packet"
            body = case.internal_report_markdown or "Internal report has not been generated."
        elif variant == "external":
            title = "wr3 responsible disclosure report"
            body = case.external_report_markdown or "External report has not been generated."
            lowered = body.lower()
            forbidden_terms = (
                "scam",
                "fraud",
                "working poc",
                "working exploit",
                "exploit recipe",
                "exploit steps",
                "mainnet exploit steps",
            )
            if any(term in lowered for term in forbidden_terms):
                raise ValueError("external_report_contains_forbidden_wording")
        else:
            raise ValueError("unsupported_disclosure_report_variant")
        return self._renderer.render_text_pdf(title, body)

    def _finding_for_packet(self, record: AuditRecord, finding_id: str | None) -> Finding:
        if finding_id:
            for finding in record.findings:
                if finding.id == finding_id:
                    return finding
            raise AuditNotFound(finding_id)
        primary = self._primary_finding(record)
        if primary is None:
            raise AuditNotFound("audit_has_no_finding_for_disclosure_packet")
        return primary

    def _packet_response(
        self,
        case: DisclosureCase,
        *,
        record: AuditRecord | None = None,
        finding: Finding | None = None,
    ) -> DisclosurePacketResponse:
        if record is None and case.audit_id is not None:
            try:
                record = self.get_record(case.audit_id)
            except AuditNotFound:
                record = None
        if finding is None and record is not None:
            finding = next((item for item in record.findings if item.id == case.finding_id), None)
        assessment = finding.disclosure_assessment if finding else None
        return DisclosurePacketResponse(
            case_id=case.id,
            audit_id=case.audit_id,
            finding_id=case.finding_id,
            readiness_state=case.readiness_state,
            candidate_detected=case.candidate_detected,
            confirmed_by_poc=case.confirmed_by_poc,
            pdfs_generated=case.pdfs_generated,
            needs_human_approval=case.needs_human_approval,
            approved_to_contact=case.approved_to_contact,
            manually_sent=case.manually_sent,
            dismissed=case.dismissed,
            project_name=case.project_name,
            chain=record.request.chain if record else None,
            address=record.request.address if record else None,
            bug_type=finding.taxonomy.wr3_category if finding else None,
            severity=finding.severity if finding else None,
            location_label=assessment.location_label if assessment else None,
            confidence_reason=assessment.technical_explanation if assessment else None,
            bounty_acceptance_reason=self._packet_bounty_reason(record, finding, case) if record and finding else None,
            bounty_platform=record.request.bounty.platform if record and record.request.bounty else None,
            bounty_program=record.request.bounty.program if record and record.request.bounty else None,
            bounty_max_payout_usd=record.request.bounty.max_payout_usd if record and record.request.bounty else None,
            bounty_submission_url=record.request.bounty.url if record and record.request.bounty else None,
            official_contact=case.project_contact,
            contact_source=case.contact_source,
            web_url=case.web_url,
            internal_pdf_url=case.internal_pdf_url,
            external_pdf_url=case.external_pdf_url,
            draft_message=case.draft_message,
            limitations=case.limitations,
        )

    def _packet_limitations(self, record: AuditRecord, finding: Finding, case: DisclosureCase) -> list[str]:
        limitations = [
            "no_auto_support_messages",
            "no_mainnet_broadcast",
            "external_report_omits_raw_poc_steps",
            "telegram_alert_omits_working_poc",
        ]
        if not self._is_confirmed_by_poc_or_fork(finding):
            limitations.append("not_confirmed_by_poc_fork_or_test")
        if not self._has_clear_impact(finding):
            limitations.append("impact_statement_needs_review")
        if not self._official_contact_allowed(case.contact_source):
            limitations.append("official_contact_not_strong_enough_for_red")
        if record.request.address is None:
            limitations.append("source_only_target_contact_must_be_verified")
        return limitations

    def _safe_disclosure_draft(self, record: AuditRecord, finding: Finding, case: DisclosureCase) -> str:
        target = record.request.address or finding.contract.address or record.audit_id
        return (
            f"Subject: responsible disclosure candidate for {record.request.chain} target {target}\n\n"
            f"Hello {case.project_contact or 'security team'},\n\n"
            "We are contacting you privately through what appears to be an official security channel. "
            "wr3 identified a security candidate during passive/local/fork-only review.\n\n"
            f"Target: {record.request.chain}:{target}\n"
            f"Category: {finding.taxonomy.wr3_category}\n"
            f"Severity candidate: {finding.severity}\n"
            f"Location: {finding.disclosure_assessment.location_label}\n"
            f"Validation: {finding.evidence.poc_status}\n\n"
            "No mainnet transaction was broadcast, no funds were moved, and this first message does not include "
            "transaction recipe details or raw private traces. Please confirm the official security/bounty intake "
            "channel and whether this target is in scope.\n\n"
            "Regards,\nwr3 research"
        )

    def _is_confirmed_by_poc_or_fork(self, finding: Finding) -> bool:
        return finding.evidence.poc_status == PocStatus.CONFIRMED or finding.exploitability == Exploitability.CONFIRMED

    def _has_clear_impact(self, finding: Finding) -> bool:
        return bool(finding.impact and len(finding.impact.strip()) >= 24)

    def _official_contact_allowed(self, source: str | None) -> bool:
        return bool(source and source in OFFICIAL_CONTACT_SOURCES)

    def _bounty_acceptance_reason(self, record: AuditRecord, finding: Finding, case: DisclosureCase) -> str:
        return self._renderer._bounty_acceptance_reason(record, finding, case)

    def _packet_bounty_reason(self, record: AuditRecord, finding: Finding, case: DisclosureCase) -> str:
        """Prepend Immunefi program/payout/submission context to the generic
        acceptance reason when the target is a known in-scope bounty asset."""
        base = self._bounty_acceptance_reason(record, finding, case)
        bounty = record.request.bounty
        if bounty is None:
            return base
        payout = f"до ${int(bounty.max_payout_usd):,}" if bounty.max_payout_usd else "выплата по программе"
        if self._is_confirmed_by_poc_or_fork(finding):
            state = "подтверждён PoC/форком — можно готовить сабмит в программу"
        else:
            state = "ещё не подтверждён — нужен confirmed PoC/форк до сабмита"
        note = (
            f"В scope {bounty.platform} «{bounty.program}» ({payout}). "
            f"Раскрытие только через {bounty.url or bounty.platform}. Статус: {state}."
        )
        return f"{note}\n\n{base}" if base else note

    def advance_disclosure_case(
        self,
        case_id: str,
        request: DisclosureAdvanceRequest,
        actor: AuthContext | None = None,
    ) -> DisclosureCase:
        case = self.get_disclosure_case(case_id, actor)
        if request.status not in DISCLOSURE_DEADLINE_DAYS:
            raise ValueError("unsupported_disclosure_status")
        case.status = request.status
        if request.note:
            case.contact_log.append(f"{utc_now().date().isoformat()} [status-note]: {request.note}")
        case.deadline_next = case.created_at + timedelta(days=DISCLOSURE_DEADLINE_DAYS[request.status])
        self._disclosure_repository.save(case)
        return case

    async def retry(self, audit_id: UUID, access: AuditAccessContext | None = None) -> AuditRecord:
        record = self.get_record(audit_id)
        self._ensure_owner(record, access)
        if record.state not in {AuditState.FAILED, AuditState.PARTIAL, AuditState.NEEDS_SOURCE}:
            record.limitations.append("retry_ignored_current_state_not_retryable")
            return record
        if record.state == AuditState.NEEDS_SOURCE:
            self._transition(record, AuditState.QUEUED, reason="source_retry_requeued")
            return record
        self._transition(record, AuditState.RETRYING, reason="manual_retry")
        self._transition(record, AuditState.QUEUED, reason="retry_requeued")
        return record

    def delete_audit(self, audit_id: UUID, access: AuditAccessContext | None = None) -> dict[str, object]:
        record = self.get_record(audit_id)
        self._ensure_owner(record, access)
        deleted = self._audit_repository.delete(audit_id)
        return {
            "audit_id": str(audit_id),
            "deleted": deleted,
            "retention_action": "owner_requested_delete",
        }

    def run_retention_sweep(self, *, dry_run: bool = False) -> RetentionRunResult:
        return RetentionService(self._audit_repository).run_once(dry_run=dry_run)

    def public_project(self, chain: Chain, address: str) -> PublicProjectSummary:
        latest = next(
            (
                record
                for record in reversed(self._audit_repository.list_records())
                if record.request.chain == chain and record.request.address == address
            ),
            None,
        )
        if latest is None:
            return PublicProjectSummary(
                chain=chain,
                address=address,
                limitations=["no_public_wr3_audit_for_contract"],
            )
        return PublicProjectSummary(
            chain=chain,
            address=address,
            score=latest.score,
            safe_harbor_status=self._safe_harbor.is_registered(chain, address),
            public_findings=redact_findings_for_public(latest.findings),
            limitations=["public_page_redacts_private_findings", *latest.limitations],
        )

    async def _process_record(self, record: AuditRecord) -> None:
        if not record.request.source:
            self._transition(record, AuditState.INGESTING, reason="ingestion_started")
            pulled = await self._pull_verified_source(record)
            if pulled is None:
                if record.request.allow_bytecode_only and record.request.chain != Chain.SOLANA:
                    record.request.source = self._bytecode_only_source(record)
                    record.source_metadata = build_source_metadata(
                        source=record.request.source,
                        origin="bytecode_only",
                        bytecode_only=True,
                    )
                    record.limitations.extend(
                        [
                            "bytecode_only_limited_scan",
                            "verified_source_missing_static_signal_limited",
                        ]
                    )
                    record.events.append(
                        AuditEvent(
                            audit_id=record.audit_id,
                            event_type="bytecode_only_fallback",
                            payload={
                                "chain": record.request.chain,
                                "address": record.request.address,
                                "source_hash": record.source_metadata.source_hash,
                            },
                        )
                    )
                else:
                    self._transition(record, AuditState.NEEDS_SOURCE, reason="source_required")
                    self._audit_repository.save(record)
                    return
            else:
                record.request.source = pulled.source
                record.source_metadata = build_source_metadata(
                    source=pulled.source,
                    origin="explorer",
                    verified_at=pulled.verified_at,
                    explorer_url=pulled.explorer_url,
                    explorer_metadata=pulled.metadata,
                )
                record.limitations.extend(
                    limitation
                    for limitation in [
                        f"source_pulled_from_{pulled.explorer_url}" if pulled.explorer_url else None,
                        *record.source_metadata.proxy_info.limitations,
                    ]
                    if limitation
                )
        else:
            self._transition(record, AuditState.INGESTING, reason="ingestion_started")
            record.source_metadata = build_source_metadata(
                source=record.request.source,
                origin="pasted",
            )
            record.limitations.extend(record.source_metadata.proxy_info.limitations)
        record.events.append(
            AuditEvent(
                audit_id=record.audit_id,
                event_type="source_metadata",
                payload={
                    "origin": record.source_metadata.source_origin,
                    "source_hash": record.source_metadata.source_hash,
                    "bytecode_only": record.source_metadata.bytecode_only,
                    "verified_at": record.source_metadata.verified_at.isoformat()
                    if record.source_metadata.verified_at
                    else None,
                    "proxy_info": record.source_metadata.proxy_info.model_dump(mode="json"),
                    "retention_until": record.retention_until.isoformat() if record.retention_until else None,
                },
            )
        )

        source_text = record.request.source or ""
        source = NormalizedSource(
            chain=record.request.chain,
            address=record.request.address,
            source=source_text,
            contract_name=self._guess_contract_name(source_text),
            file_name="Contract.sol",
        )

        self._transition(record, AuditState.STATIC_RUNNING, reason="static_started")
        await self._run_static(record, source)

        self._transition(record, AuditState.TRIAGE_RUNNING, reason="triage_started")
        route = self._llm_triage.route(record)
        prompt_preview = self._llm_triage.build_prompt_preview(record, source_text)
        triage_result = await self._llm_triage.triage(
            record,
            source_text,
            self._deterministic_triage,
            route=route,
        )
        record.limitations.extend(triage_result.limitations)
        record.events.append(
            AuditEvent(
                audit_id=record.audit_id,
                event_type="llm_triage_route",
                payload={
                    "provider": route.provider,
                    "model": route.model,
                    "enabled": route.enabled,
                    "zdr_required": route.zdr_required,
                    "provider_invoked": triage_result.provider_invoked,
                    "fallback": "deterministic" if triage_result.error_type or not route.enabled else "provider_then_deterministic",
                    "error_type": triage_result.error_type,
                    "agent_roles": list(self._llm_triage.agent_roles),
                    "agent_payloads_received": sorted(triage_result.agent_payloads),
                    "prompt_wrapped_untrusted_source": "UNTRUSTED_CONTRACT_SOURCE_BEGIN" in prompt_preview,
                },
            )
        )
        consensus = self._triage_consensus.run(triage_result.findings)
        record.findings = consensus.findings
        record.events.append(
            AuditEvent(
                audit_id=record.audit_id,
                event_type="triage_consensus",
                payload={
                    **consensus.summary,
                    "agents": list(self._triage_consensus.agents),
                    "verdicts": [
                        {
                            "agent": verdict.agent,
                            "finding_id": verdict.finding_id,
                            "action": verdict.action,
                            "reason": verdict.reason,
                        }
                        for verdict in consensus.verdicts
                    ],
                },
            )
        )

        if self._poc_worker.should_consider(record):
            self._transition(record, AuditState.POC_RUNNING, reason="poc_started")
            candidates = high_risk_poc_candidates(record.findings)
            poc_result = await self._poc_worker.run(record, candidates)
            self._poc_worker.record_result(record, poc_result, candidates)
            self._apply_poc_confirmation(
                record, poc_result.confirmed_finding_ids, poc_result.artifact_uri
            )
            if record.request.requested_depth == "deep":
                self._transition(record, AuditState.FUZZING_RUNNING, reason="fuzzing_started")
                fuzz_result = await self._fuzz_worker.run(record, record.findings)
                self._fuzz_worker.record_result(record, fuzz_result)
                self._apply_fuzz_counterexample(record, fuzz_result)
        else:
            record.limitations.append("poc_requires_standard_or_deep_depth")

        self._annotate_findings_for_disclosure(record)
        self._transition(record, AuditState.SCORING, reason="scoring_started")
        record.score = score_audit(
            record.findings,
            ScoreContext(
                unverified_source=record.source_metadata.bytecode_only,
                unlimited_owner_mint=any(
                    finding.taxonomy.wr3_category == "centralization"
                    for finding in record.findings
                    if finding.severity in {Severity.LOW, Severity.MEDIUM}
                ),
            ),
        )
        if any(
            finding.severity in {Severity.CRITICAL, Severity.HIGH}
            and finding.human_review_status != "approved"
            for finding in record.findings
        ):
            record.limitations.append("high_risk_findings_require_human_review_before_public_claim")
        self._transition(record, AuditState.COMPLETED, reason="report_ready")
        self._audit_repository.save(record)
        await self._maybe_alert_owner(record)

    def _apply_poc_confirmation(
        self,
        record: AuditRecord,
        confirmed_ids: tuple[str, ...],
        artifact_uri: str | None = None,
    ) -> None:
        """Write PoC confirmation back onto findings so disclosure-readiness,
        scoring and the rendered report — which key off ``exploitability ==
        CONFIRMED`` and ``evidence.poc_status == CONFIRMED`` — actually react to a
        confirmed exploit instead of the confirmation being recorded only as an
        event. Both fields are updated together so a finding never claims a
        confirmed exploitability while its evidence still reads ``not_attempted``."""
        if not confirmed_ids:
            return
        confirmed = set(confirmed_ids)
        for index, finding in enumerate(record.findings):
            already = (
                finding.exploitability == Exploitability.CONFIRMED
                and finding.evidence.poc_status == PocStatus.CONFIRMED
            )
            if finding.id in confirmed and not already:
                evidence = finding.evidence.model_copy(
                    update={
                        "poc_status": PocStatus.CONFIRMED,
                        "poc_artifact_uri": artifact_uri or finding.evidence.poc_artifact_uri,
                    }
                )
                record.findings[index] = finding.model_copy(
                    update={
                        "exploitability": Exploitability.CONFIRMED,
                        "evidence": evidence,
                    }
                )

    def _apply_fuzz_counterexample(self, record: AuditRecord, result: FuzzWorkerResult) -> None:
        """When Medusa breaks the solvency invariant it has produced a concrete,
        shrunk call sequence that extracts value — an autonomously discovered,
        confirmed accounting defect. Record it as a first-class finding so scoring,
        disclosure and the report react to it, not just an engine event."""
        if result.status != "counterexample_found":
            return
        if any(
            finding.taxonomy.wr3_category == "accounting" and "medusa" in finding.sources
            for finding in record.findings
        ):
            return  # already raised this campaign's solvency finding
        properties = ", ".join(result.violated_properties) or "property_bank_solvent"
        description = (
            f"Medusa's invariant fuzzer broke the solvency invariant ({properties}): after a "
            "fuzzed call sequence the contract owed depositors more than the ETH it held, i.e. "
            "an actor could withdraw more value than it deposited. This is a confirmed "
            "accounting/solvency defect, reproduced deterministically by the fuzzer."
        )
        counterexample = (result.counterexample or "").strip()
        if counterexample:
            description += f"\n\nMinimal reproducing call sequence (shrunk by Medusa):\n{counterexample[:1500]}"
        record.findings.append(
            Finding(
                audit_id=str(record.audit_id),
                chain=record.request.chain,
                contract=self._fuzz_target_contract(record),
                taxonomy=Taxonomy(wr3_category="accounting"),
                severity=Severity.HIGH,
                confidence=0.95,
                exploitability=Exploitability.CONFIRMED,
                sources=["medusa"],
                evidence=Evidence(fuzzer_counterexample_uri=result.artifact_uri),
                summary="Medusa broke the solvency invariant: withdrawable value exceeds deposits",
                description=description,
                impact="An attacker can extract more funds than they deposited, draining other users' balances.",
                recommendation=(
                    "Fix the deposit/withdraw accounting (zero balances before the external transfer, "
                    "apply checks-effects-interactions) and re-run the fuzzer to confirm the invariant holds."
                ),
            )
        )

    def _fuzz_target_contract(self, record: AuditRecord) -> ContractRef:
        for finding in record.findings:
            name = finding.contract.name if finding.contract else None
            if name and name != "Unknown":
                return finding.contract.model_copy()
        source = ensure_solidity_pragma(record.request.source or "")
        return ContractRef(name=extract_primary_contract(source) or "Unknown", address=record.request.address)

    async def _maybe_alert_owner(self, record: AuditRecord) -> None:
        """Alert the platform owner (reviewer Telegram) when an autonomous/monitoring
        audit surfaces high/critical findings, so they don't have to poll. Never
        contacts the audited protocol — disclosure stays manual."""
        if record.request.user_intent != UserIntent.MONITORING:
            return
        high = [
            finding
            for finding in record.findings
            if finding.severity in {Severity.CRITICAL, Severity.HIGH}
        ]
        if not high:
            return
        top = high[0]
        title = f"wr3 alert: {len(high)} high/critical on {record.request.chain}"
        body = (
            f"{record.request.address or 'source scan'}\n"
            f"Top: [{top.severity}] {top.summary}\n"
            f"Audit: {record.audit_id}"
        )
        try:
            await self._notifications.send_owner_alert(title=title, body=body)
        except Exception:
            record.limitations.append("owner_alert_delivery_failed")

    def _annotate_findings_for_disclosure(self, record: AuditRecord) -> None:
        ai_fallback = any(
            limitation in record.limitations
            for limitation in {
                "llm_triage_disabled_using_deterministic_fallback",
                "llm_triage_provider_error_using_deterministic_fallback",
            }
        )
        failed_engines = [run.engine for run in record.engine_runs if run.status == "failed"]
        for index, finding in enumerate(record.findings):
            record.findings[index] = finding.model_copy(
                update={
                    "disclosure_assessment": self._finding_disclosure_assessment(
                        finding,
                        ai_fallback=ai_fallback,
                        failed_engines=failed_engines,
                        source_is_verified=not record.source_metadata.bytecode_only,
                    )
                }
            )

    def _finding_disclosure_assessment(
        self,
        finding: Finding,
        *,
        ai_fallback: bool,
        failed_engines: list[str],
        source_is_verified: bool,
    ) -> DisclosureAssessment:
        location_known = bool(finding.location.start_line or finding.location.function)
        heuristic_only = all(source.startswith("wr3_heuristic") for source in finding.sources)
        non_heuristic_static = any(source in {"aderyn", "wake", "slither"} for source in finding.sources)
        poc_confirmed = finding.evidence.poc_status == "confirmed"
        static_ai_strong = (
            non_heuristic_static
            and not ai_fallback
            and finding.confidence >= 0.70
            and finding.exploitability in {Exploitability.LIKELY, Exploitability.CONFIRMED, Exploitability.THEORETICAL}
        )

        evidence_gaps: list[str] = []
        if not location_known:
            evidence_gaps.append("Нужно точное место в коде: файл, строка или функция.")
        if heuristic_only:
            evidence_gaps.append("Сигнал пока найден только heuristic detector, нужен Aderyn/Wake/Slither или ручной AST-review.")
        if ai_fallback:
            evidence_gaps.append("ИИ-триаж не подтвердил сигнал: использован deterministic fallback.")
        if failed_engines:
            evidence_gaps.append(f"Часть движков упала: {', '.join(sorted(set(failed_engines)))}.")
        if finding.evidence.poc_status != "confirmed":
            evidence_gaps.append("Нет локального PoC/fork-test подтверждения.")
        if not source_is_verified:
            evidence_gaps.append("Исходный код не верифицирован, доверие к анализу ниже.")

        if finding.exploitability == Exploitability.DISMISSED or finding.dismissal_reason:
            verdict = "do_not_write"
            verdict_label = "Не писать"
            readiness = "dismissed"
            readiness_label = "Отклонено"
            can_contact = False
            false_positive_risk = "high"
            next_step = "Оставить причину отклонения и не создавать disclosure."
        elif poc_confirmed or static_ai_strong:
            verdict = "can_write"
            verdict_label = "Можно писать"
            readiness = "ready_to_contact"
            readiness_label = "Готово к письму"
            can_contact = True
            false_positive_risk = "low" if poc_confirmed else "medium"
            next_step = "Собрать приватный disclosure draft и отправлять только в официальный security contact."
        else:
            verdict = "too_early"
            verdict_label = "Рано писать"
            readiness = "candidate" if finding.severity in {Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM} else "signal"
            readiness_label = "Кандидат" if readiness == "candidate" else "Сигнал"
            can_contact = False
            false_positive_risk = "high" if heuristic_only or not location_known else "medium"
            next_step = "Сначала ручная проверка, точная location и независимое подтверждение сигнала."

        location_label = (
            f"{finding.location.file or finding.contract.file or 'исходник'}"
            + (f":{finding.location.start_line}" if finding.location.start_line else "")
            + (f" · {finding.location.function}" if finding.location.function else "")
            if location_known
            else "Точное место не определено"
        )
        plain = self._plain_explanation(finding, heuristic_only=heuristic_only, location_known=location_known)
        technical = self._technical_explanation(
            finding,
            heuristic_only=heuristic_only,
            ai_fallback=ai_fallback,
            failed_engines=failed_engines,
            location_known=location_known,
        )
        checklist = self._manual_checklist(finding)

        return DisclosureAssessment(
            verdict=verdict,
            verdict_label=verdict_label,
            readiness=readiness,
            readiness_label=readiness_label,
            can_contact_support=can_contact,
            false_positive_risk=false_positive_risk,
            plain_explanation=plain,
            technical_explanation=technical,
            next_step=next_step,
            manual_checklist=checklist,
            evidence_gaps=evidence_gaps,
            location_status="known" if location_known else "missing",
            location_label=location_label,
        )

    def _plain_explanation(self, finding: Finding, *, heuristic_only: bool, location_known: bool) -> str:
        if finding.taxonomy.wr3_category == "upgradeability":
            base = (
                "wr3 увидел proxy/delegatecall-паттерн. Это не баг само по себе, "
                "но баг возможен, если target implementation или admin-контроль можно подменить небезопасно."
            )
        elif finding.taxonomy.wr3_category == "reentrancy":
            base = (
                "wr3 увидел low-level внешний вызов. Это кандидат на reentrancy только если вызов происходит "
                "до безопасного обновления состояния или без защитного lock."
            )
        elif finding.taxonomy.wr3_category == "access_control":
            base = "wr3 увидел риск в access-control. Нужно проверить, кто реально может вызвать опасный путь."
        else:
            base = "wr3 увидел подозрительный security-паттерн. Это кандидат, а не подтверждённая уязвимость."
        qualifiers = []
        if heuristic_only:
            qualifiers.append("пока это heuristic-only сигнал")
        if not location_known:
            qualifiers.append("точное место в коде ещё не найдено")
        return base + (" Сейчас " + ", ".join(qualifiers) + "." if qualifiers else "")

    def _technical_explanation(
        self,
        finding: Finding,
        *,
        heuristic_only: bool,
        ai_fallback: bool,
        failed_engines: list[str],
        location_known: bool,
    ) -> str:
        parts = [
            f"Категория: {finding.taxonomy.wr3_category}.",
            f"Источники: {', '.join(finding.sources)}.",
            f"Exploitability: {finding.exploitability}; confidence: {finding.confidence:.2f}.",
        ]
        if finding.taxonomy.wr3_category == "upgradeability":
            parts.append("Проверить proxy admin, implementation address, возможность upgrade и storage-layout assumptions.")
        if finding.taxonomy.wr3_category == "reentrancy":
            parts.append("Проверить порядок effects/interactions, external call target, balance/share accounting и наличие guard.")
        if heuristic_only:
            parts.append("Structured AST/static confirmation пока отсутствует.")
        if ai_fallback:
            parts.append("LLM route не дал provider-confirmation; использован deterministic fallback.")
        if failed_engines:
            parts.append(f"Failed engines: {', '.join(sorted(set(failed_engines)))}.")
        if not location_known:
            parts.append("Location missing: не показывать как готовый report до ручного source mapping.")
        return " ".join(parts)

    def _manual_checklist(self, finding: Finding) -> list[str]:
        common = [
            "Проверить, что цель входит в scope программы.",
            "Найти точный файл/строку/функцию и сохранить evidence.",
            "Проверить, есть ли реальный impact, а не только подозрительный паттерн.",
        ]
        if finding.taxonomy.wr3_category == "upgradeability":
            return [
                *common,
                "Проверить proxy admin / owner и кто может менять implementation.",
                "Сравнить storage layout proxy и implementation.",
                "Проверить, ограничен ли delegatecall target allowlist/codehash.",
            ]
        if finding.taxonomy.wr3_category == "reentrancy":
            return [
                *common,
                "Проверить, обновляется ли состояние до external call.",
                "Проверить наличие reentrancy guard или pull-payment паттерна.",
                "Попробовать безопасный local/fork-test без broadcast.",
            ]
        if finding.taxonomy.wr3_category == "access_control":
            return [
                *common,
                "Проверить роли, owner/admin, multisig и tx.origin/msg.sender assumptions.",
                "Проверить негативный тест: кто не должен иметь доступ.",
            ]
        return common

    async def _pull_verified_source(self, record: AuditRecord):
        if not record.request.address:
            record.limitations.append("source_required_no_address_for_explorer_pull")
            return None
        supported = [puller for puller in self._explorers if puller.supports(record.request.chain)]
        if not supported:
            record.limitations.append(f"verified_source_pull_not_configured_for_{record.request.chain}")
            return None
        for puller in supported:
            result = await puller.pull(chain=record.request.chain, address=record.request.address)
            if result.status == "verified" and result.source:
                record.events.append(
                    AuditEvent(
                        audit_id=record.audit_id,
                        event_type="source_pulled",
                        payload={
                            "puller": puller.name,
                            "contract_name": result.contract_name,
                            "file_name": result.file_name,
                            "explorer_url": result.explorer_url,
                        },
                    )
                )
                return result
            record.limitations.append(f"{puller.name}:{result.status}:{result.reason}")
        record.limitations.append("verified_source_pull_failed_upload_source")
        return None

    def _bytecode_only_source(self, record: AuditRecord) -> str:
        return "\n".join(
            [
                "// wr3 bytecode-only limited scan placeholder",
                "// Verified source was unavailable; static source-level analysis is intentionally limited.",
                f"// chain: {record.request.chain}",
                f"// address: {record.request.address}",
                "contract Wr3BytecodeOnlyPlaceholder {}",
            ]
        )

    async def _run_static(self, record: AuditRecord, source: NormalizedSource) -> None:
        options = EngineRunOptions(audit_id=str(record.audit_id))
        supported = [adapter for adapter in self._adapters if adapter.supports(source)]
        raw_results = await asyncio.gather(
            *(adapter.run(source, options) for adapter in supported),
            return_exceptions=True,
        )

        for adapter, raw_result in zip(supported, raw_results):
            if isinstance(raw_result, Exception):
                result = EngineRunResult(
                    engine=adapter.name,
                    status="failed",
                    error=f"{raw_result.__class__.__name__}: {raw_result}",
                )
            else:
                result = raw_result
            record.findings.extend(result.findings)
            record.engine_runs.append(
                EngineRunSummary(
                    audit_id=record.audit_id,
                    engine=result.engine,
                    status=result.status,
                    duration_ms=result.duration_ms,
                    artifact_uri=self._store_raw_output_artifact(record, result),
                    error=result.error,
                )
            )
            if result.status == "failed":
                record.failed_stages.append(f"static:{result.engine}")
            if result.status == "skipped":
                record.limitations.append(f"{result.engine}_skipped:{result.error}")

        if not record.findings:
            record.failed_stages.append("static:no_findings_or_engines")

    def _store_raw_output_artifact(self, record: AuditRecord, result) -> str | None:
        if not result.raw_output:
            return None
        try:
            artifact = self._artifact_vault.store_json(
                audit_id=str(record.audit_id),
                kind="raw_output",
                payload={
                    "engine": result.engine,
                    "status": result.status,
                    "raw_output": result.raw_output,
                    "error": result.error,
                },
                private=True,
            )
        except ArtifactEncryptionRequired:
            record.limitations.append(f"{result.engine}_raw_output_artifact_requires_encryption")
            return None
        return artifact.uri

    def _highest_severity(self, findings: list[Finding]) -> Severity | None:
        order = {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }
        active = [finding.severity for finding in findings if finding.exploitability != Exploitability.DISMISSED]
        if not active:
            return None
        return max(active, key=lambda item: order[item])

    def _deterministic_triage(self, findings: list[Finding]) -> list[Finding]:
        deduped: dict[tuple[str, str, str], Finding] = {}
        for finding in findings:
            key = (finding.summary.lower(), finding.taxonomy.wr3_category, finding.severity)
            current = deduped.get(key)
            if current is None:
                deduped[key] = finding
                continue
            # Same issue reported by multiple engines: keep the higher-confidence
            # finding but union the engine sources so cross-engine corroboration is
            # preserved instead of silently discarded.
            merged_sources = list(dict.fromkeys([*current.sources, *finding.sources]))
            winner = finding if finding.confidence > current.confidence else current
            deduped[key] = winner.model_copy(update={"sources": merged_sources})

        triaged: list[Finding] = []
        for finding in deduped.values():
            if finding.severity == Severity.INFO:
                triaged.append(finding)
                continue
            if finding.confidence < 0.3:
                triaged.append(
                    finding.model_copy(
                        update={
                            "exploitability": Exploitability.DISMISSED,
                            "dismissal_reason": "confidence_below_mvp_threshold",
                        }
                    )
                )
            else:
                triaged.append(finding)
        return triaged

    def _transition(self, record: AuditRecord, to_state: AuditState, *, reason: str) -> None:
        assert_transition(record.state, to_state)
        record.state = to_state
        record.updated_at = utc_now()
        record.events.append(
            AuditEvent(
                audit_id=record.audit_id,
                event_type="state_transition",
                payload={"to": to_state, "reason": reason},
            )
        )
        self._audit_repository.save(record)

    def _access_summary(
        self,
        record: AuditRecord,
        access: AuditAccessContext | None,
    ) -> AuditAccessSummary:
        is_owner = self._is_owner(record, access)
        is_public_view = (
            record.request.visibility == "public"
            or self._public_token_matches(record, access.public_token if access else None)
        )
        return AuditAccessSummary(
            is_owner=is_owner,
            is_public_view=is_public_view,
            can_view_private_findings=is_owner,
            can_view_raw_outputs=is_owner,
            auth_provider=access.actor.provider if access and access.actor.provider else None,
        )

    def _ensure_owner(self, record: AuditRecord, access: AuditAccessContext | None) -> None:
        if not self._is_owner(record, access):
            raise AuditAccessDenied("owner_access_required")

    def _ensure_owner_or_report_token(
        self,
        record: AuditRecord,
        access: AuditAccessContext | None,
    ) -> None:
        if self._is_owner(record, access):
            return
        if access is not None and self._public_token_matches(record, access.public_token):
            return
        raise AuditAccessDenied("owner_or_report_token_required")

    def _is_owner(self, record: AuditRecord, access: AuditAccessContext | None) -> bool:
        if access is None:
            return False
        if access.actor.is_reviewer:
            return True
        if record.user_id and access.actor.user_id == record.user_id:
            return True
        if access.owner_token and compare_digest(record.owner_access_token, access.owner_token):
            return True
        return False

    def _public_token_matches(self, record: AuditRecord, token: str | None) -> bool:
        return bool(record.public_report_token and token and compare_digest(record.public_report_token, token))

    def _guess_contract_name(self, source: str) -> str:
        marker = "contract "
        if marker not in source:
            return "Contract"
        tail = source.split(marker, 1)[1]
        return tail.split("{", 1)[0].split()[0].strip() or "Contract"
