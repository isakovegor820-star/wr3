from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from wr3_api.api.dependencies import get_optional_auth
from wr3_api.api.routes.audits import service as audit_service
from wr3_api.domain.enums import Chain, UserIntent, Visibility
from wr3_api.domain.schemas import (
    CreateAuditRequest,
    ScoutQueuedAudit,
    ScoutReviewItem,
    ScoutReviewQueue,
    ScoutRunAllRequest,
    ScoutRunRequest,
    ScoutRunResult,
    ScoutTarget,
)
from wr3_api.services.auth import AuthContext
from wr3_api.services.dispatcher import dispatch_audit_processing
from wr3_api.services.target_discovery import TargetDiscoveryService

router = APIRouter(prefix="/v1/monitoring", tags=["monitoring"])


@router.get("/targets", response_model=list[ScoutTarget])
async def discover_targets(
    limit: int = Query(default=10, ge=1, le=50),
    min_tvl_usd: float = Query(default=0, ge=0),
    chain: list[Chain] = Query(default=[]),
) -> list[ScoutTarget]:
    try:
        return await TargetDiscoveryService().discover_defillama_protocols(
            limit=limit,
            min_tvl_usd=min_tvl_usd,
            chains=chain,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"target_discovery_failed:{exc.__class__.__name__}") from exc


@router.post("/scout/run-once", response_model=ScoutRunResult)
async def run_scout_once(
    request: ScoutRunRequest,
    background_tasks: BackgroundTasks,
    actor: AuthContext = Depends(get_optional_auth),
) -> ScoutRunResult:
    if request.source != "defillama_protocols":
        raise HTTPException(status_code=400, detail="unsupported_scout_source")
    try:
        targets = await TargetDiscoveryService().discover_defillama_protocols(
            limit=request.limit,
            min_tvl_usd=request.min_tvl_usd,
            chains=request.chains,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"target_discovery_failed:{exc.__class__.__name__}") from exc

    audits = await _queue_targets(
        targets,
        background_tasks=background_tasks,
        actor=actor,
        dry_run=request.dry_run,
        requested_depth=request.requested_depth,
        tier=request.tier,
    )

    return ScoutRunResult(
        source=request.source,
        discovered_count=len(targets),
        queued_count=len(audits),
        skipped_count=len(targets) - len(audits),
        targets=targets,
        audits=audits,
        limitations=[
            "free_source_defillama_protocols_no_api_key",
            "passive_analysis_only",
            "no_auto_support_messages",
            "contacts_and_scope_require_manual_verification",
        ],
    )


@router.post("/scout/run-all", response_model=ScoutRunResult)
async def run_all_networks(
    request: ScoutRunAllRequest,
    background_tasks: BackgroundTasks,
    actor: AuthContext = Depends(get_optional_auth),
) -> ScoutRunResult:
    if request.source != "defillama_protocols":
        raise HTTPException(status_code=400, detail="unsupported_scout_source")
    try:
        targets = await TargetDiscoveryService().discover_all_supported_networks(
            per_chain_limit=request.per_chain_limit,
            min_tvl_usd=request.min_tvl_usd,
            chains=request.chains,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"target_discovery_failed:{exc.__class__.__name__}") from exc

    audits = await _queue_targets(
        targets,
        background_tasks=background_tasks,
        actor=actor,
        dry_run=request.dry_run,
        requested_depth=request.requested_depth,
        tier=request.tier,
    )
    return ScoutRunResult(
        source=request.source,
        discovered_count=len(targets),
        queued_count=len(audits),
        skipped_count=len(targets) - len(audits),
        targets=targets,
        audits=audits,
        limitations=[
            "all_supported_networks_cycle",
            "deep_mode_is_best_effort_local_pipeline",
            "free_source_defillama_protocols_no_api_key",
            "passive_analysis_only",
            "no_auto_support_messages",
            "contacts_and_scope_require_manual_verification",
        ],
    )


@router.get("/review-queue", response_model=ScoutReviewQueue)
async def review_queue(
    limit: int = Query(default=100, ge=1, le=500),
    actor: AuthContext = Depends(get_optional_auth),
) -> ScoutReviewQueue:
    try:
        rows = audit_service.list_audits_for_dashboard(actor=actor)[:limit]
    except Exception as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    queue = ScoutReviewQueue(
        limitations=[
            "review_queue_uses_private_local_audits",
            "ready_to_write_requires_human_review_before_sending",
            "skip_does_not_mean_contract_is_safe",
        ]
    )
    for row in rows:
        item = _review_item(row)
        if item.bucket == "ready_to_write":
            queue.ready_to_write.append(item)
        elif item.bucket == "skip":
            queue.skip.append(item)
        else:
            queue.needs_validation.append(item)
    queue.totals = {
        "ready_to_write": len(queue.ready_to_write),
        "needs_validation": len(queue.needs_validation),
        "skip": len(queue.skip),
        "total": len(rows),
    }
    return queue


async def _queue_targets(
    targets: list[ScoutTarget],
    *,
    background_tasks: BackgroundTasks,
    actor: AuthContext,
    dry_run: bool,
    requested_depth,
    tier,
) -> list[ScoutQueuedAudit]:
    audits: list[ScoutQueuedAudit] = []
    if dry_run:
        return audits
    for target in targets:
        audit_request = CreateAuditRequest(
            chain=target.chain,
            address=target.address,
            source=None,
            allow_bytecode_only=True,
            requested_depth=requested_depth,
            visibility=Visibility.PRIVATE,
            user_intent=UserIntent.MONITORING,
            tier=tier,
        )
        record = await audit_service.create_audit(audit_request, actor)
        record.limitations.extend(
            [
                f"scout_target:{target.source}:{target.protocol_name}",
                "scout_support_contact_must_be_verified_manually",
            ]
        )
        audit_service.save_record(record)
        dispatch_limitations: list[str] = []
        if record.state == "queued":
            dispatch_limitations = dispatch_audit_processing(
                audit_id=record.audit_id,
                background_tasks=background_tasks,
                local_processor=audit_service.process_audit,
            )
            record.limitations.extend(dispatch_limitations)
        audits.append(
            ScoutQueuedAudit(
                audit_id=record.audit_id,
                owner_access_token=record.owner_access_token,
                chain=target.chain,
                address=target.address,
                protocol_name=target.protocol_name,
                status_url=f"/v1/audits/{record.audit_id}",
                report_url=f"/v1/audits/{record.audit_id}/report",
                limitations=[*target.limitations, *record.limitations, *dispatch_limitations],
            )
        )
    return audits


def _review_item(row: dict[str, object]) -> ScoutReviewItem:
    finding_count = int(row.get("finding_count") or 0)
    state = row["state"]
    can_contact = bool(row.get("can_create_disclosure"))
    verdict = str(row.get("primary_verdict") or "no_signal")
    highest = row.get("highest_severity")
    if can_contact:
        bucket = "ready_to_write"
        action_label = "Можно готовить приватное обращение"
        why = "Есть сигнал, который wr3 считает достаточно готовым для черновика disclosure."
    elif verdict in {"do_not_write", "dismissed"} or (
        state == "completed" and (finding_count == 0 or highest in {None, "info"})
    ):
        bucket = "skip"
        action_label = "Пропустить"
        why = "Нет готового bug-candidate или сигнал отклонён. Это не доказательство безопасности контракта."
    else:
        bucket = "needs_validation"
        action_label = "Проверить вручную"
        why = str(row.get("primary_explanation") or "Нужна ручная проверка перед обращением.")

    audit_id = row["audit_id"]
    owner_token = row.get("owner_access_token")
    report_url = f"/audits/{audit_id}"
    if owner_token:
        report_url = f"{report_url}?owner_token={owner_token}"
    return ScoutReviewItem(
        bucket=bucket,
        action_label=action_label,
        audit_id=audit_id,
        owner_access_token=owner_token if isinstance(owner_token, str) else None,
        chain=row["chain"],
        address=row.get("address") if isinstance(row.get("address"), str) else None,
        state=state,
        score=(row.get("score") or {}).get("final_score") if isinstance(row.get("score"), dict) else None,
        finding_count=finding_count,
        highest_severity=row.get("highest_severity"),
        primary_title=row.get("primary_finding_title") if isinstance(row.get("primary_finding_title"), str) else None,
        verdict_label=str(row.get("primary_verdict_label") or "Нет сигнала"),
        readiness_label=str(row.get("primary_readiness_label") or "Нет сигнала"),
        can_contact_support=can_contact,
        why=why,
        next_step=str(row.get("primary_next_step") or "Открыть отчёт и проверить вручную."),
        evidence_gaps=list(row.get("primary_evidence_gaps") or []),
        support_route=[
            "Официальный сайт: Security / Contact / Docs.",
            "GitHub SECURITY.md или вкладка Security.",
            "Bug bounty платформа: Immunefi / Hats / Cantina / Sherlock / Code4rena.",
        ],
        report_url=report_url,
    )
