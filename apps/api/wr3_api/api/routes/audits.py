from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from wr3_api.api.dependencies import get_optional_auth
from wr3_api.domain.enums import AuditState, Chain, Severity
from wr3_api.domain.schemas import CreateAuditRequest, CreateAuditResponse, FindingReviewRequest
from wr3_api.services.audit_service import AuditAccessDenied, AuditNotFound, AuditService
from wr3_api.services.auth import AuditAccessContext, AuthContext
from wr3_api.services.dispatcher import dispatch_audit_processing

router = APIRouter(prefix="/v1/audits", tags=["audits"])
service = AuditService()


def _not_found(exc: AuditNotFound) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


def _access_denied(exc: AuditAccessDenied) -> HTTPException:
    return HTTPException(status_code=403, detail=str(exc))


def _access(actor: AuthContext, owner_token: str | None, public_token: str | None) -> AuditAccessContext:
    return AuditAccessContext(actor=actor, owner_token=owner_token, public_token=public_token)


@router.post("", response_model=CreateAuditResponse)
async def create_audit(
    request: CreateAuditRequest,
    background_tasks: BackgroundTasks,
    actor: AuthContext = Depends(get_optional_auth),
) -> CreateAuditResponse:
    record = await service.create_audit(request, actor)
    if record.state == "queued":
        record.limitations.extend(
            dispatch_audit_processing(
                audit_id=record.audit_id,
                background_tasks=background_tasks,
                local_processor=service.process_audit,
            )
        )
    return CreateAuditResponse(
        audit_id=record.audit_id,
        state=record.state,
        status_url=f"/v1/audits/{record.audit_id}",
        estimated_wait_seconds=90,
        limitations=record.limitations,
        owner_access_token=record.owner_access_token,
        public_report_token=record.public_report_token,
    )


@router.get("")
async def list_audits(
    chain: Chain | None = Query(default=None),
    state: AuditState | None = Query(default=None),
    severity: Severity | None = Query(default=None),
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.list_audits_for_dashboard(
            chain=chain,
            state=state,
            severity=severity,
            actor=actor,
        )
    except AuditAccessDenied as exc:
        raise _access_denied(exc) from exc


@router.get("/{audit_id}")
async def get_audit(
    audit_id: UUID,
    owner_token: str | None = Query(default=None),
    public_token: str | None = Query(default=None),
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.get_summary(audit_id, _access(actor, owner_token, public_token))
    except AuditNotFound as exc:
        raise _not_found(exc) from exc
    except AuditAccessDenied as exc:
        raise _access_denied(exc) from exc


@router.get("/{audit_id}/findings")
async def get_findings(
    audit_id: UUID,
    public: bool = Query(default=False),
    owner_token: str | None = Query(default=None),
    public_token: str | None = Query(default=None),
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.get_findings(
            audit_id,
            public=public,
            access=_access(actor, owner_token, public_token),
        )
    except AuditNotFound as exc:
        raise _not_found(exc) from exc
    except AuditAccessDenied as exc:
        raise _access_denied(exc) from exc


@router.get("/{audit_id}/events")
async def get_events(
    audit_id: UUID,
    owner_token: str | None = Query(default=None),
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.get_events(audit_id, _access(actor, owner_token, None))
    except AuditNotFound as exc:
        raise _not_found(exc) from exc
    except AuditAccessDenied as exc:
        raise _access_denied(exc) from exc


@router.get("/{audit_id}/report")
async def get_report(
    audit_id: UUID,
    format: str = Query(default="markdown"),
    owner_token: str | None = Query(default=None),
    public_token: str | None = Query(default=None),
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        body = service.render_report(audit_id, fmt=format, access=_access(actor, owner_token, public_token))
    except AuditNotFound as exc:
        raise _not_found(exc) from exc
    except AuditAccessDenied as exc:
        raise _access_denied(exc) from exc
    if format == "html":
        return Response(content=body, media_type="text/html")
    return Response(content=body, media_type="text/markdown")


@router.get("/{audit_id}/raw-outputs")
async def get_raw_outputs(
    audit_id: UUID,
    owner_token: str | None = Query(default=None),
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.raw_outputs_metadata(audit_id, _access(actor, owner_token, None))
    except AuditNotFound as exc:
        raise _not_found(exc) from exc
    except AuditAccessDenied as exc:
        raise _access_denied(exc) from exc


@router.post("/{audit_id}/findings/{finding_id}/review")
async def review_finding(
    audit_id: UUID,
    finding_id: str,
    request: FindingReviewRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.review_finding(audit_id, finding_id, request, actor)
    except AuditNotFound as exc:
        raise _not_found(exc) from exc
    except AuditAccessDenied as exc:
        raise _access_denied(exc) from exc


@router.post("/{audit_id}/retry")
async def retry_audit(
    audit_id: UUID,
    background_tasks: BackgroundTasks,
    owner_token: str | None = Query(default=None),
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        record = await service.retry(audit_id, _access(actor, owner_token, None))
        if record.state == "queued":
            record.limitations.extend(
                dispatch_audit_processing(
                    audit_id=record.audit_id,
                    background_tasks=background_tasks,
                    local_processor=service.process_audit,
                )
            )
    except AuditNotFound as exc:
        raise _not_found(exc) from exc
    except AuditAccessDenied as exc:
        raise _access_denied(exc) from exc
    return record.to_summary(progress=100, access=service.get_summary(audit_id, _access(actor, owner_token, None)).access)


@router.delete("/{audit_id}")
async def delete_audit(
    audit_id: UUID,
    owner_token: str | None = Query(default=None),
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return JSONResponse(service.delete_audit(audit_id, _access(actor, owner_token, None)))
    except AuditNotFound as exc:
        raise _not_found(exc) from exc
    except AuditAccessDenied as exc:
        raise _access_denied(exc) from exc
