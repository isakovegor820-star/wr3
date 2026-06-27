from fastapi import APIRouter, Depends, HTTPException, Response

from wr3_api.api.dependencies import get_optional_auth
from wr3_api.api.routes.audits import service
from wr3_api.domain.schemas import (
    DisclosureAdvanceRequest,
    DisclosureCaseRequest,
    DisclosureContactLogRequest,
    DisclosureManualSentRequest,
    DisclosurePacketActionRequest,
    DisclosurePacketRequest,
    DisclosurePacketResponse,
)
from wr3_api.services.audit_service import AuditAccessDenied, AuditNotFound
from wr3_api.services.auth import AuthContext

router = APIRouter(prefix="/v1/disclosure-cases", tags=["disclosure"])


@router.post("/prepare", response_model=DisclosurePacketResponse)
async def prepare_disclosure_packet(
    request: DisclosurePacketRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.prepare_disclosure_packet(request, actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuditNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("")
async def create_disclosure_case(
    request: DisclosureCaseRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.create_disclosure_case(request, actor)
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("")
async def list_disclosure_cases(actor: AuthContext = Depends(get_optional_auth)):
    try:
        return service.list_disclosure_cases(actor)
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{case_id}/packet", response_model=DisclosurePacketResponse)
async def get_disclosure_packet(
    case_id: str,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.get_disclosure_packet(case_id, actor)
    except AuditNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{case_id}")
async def get_disclosure_case(
    case_id: str,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.get_disclosure_case(case_id, actor)
    except AuditNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{case_id}/reports/{variant}.pdf")
async def get_disclosure_report_pdf(
    case_id: str,
    variant: str,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        body = service.render_disclosure_pdf(case_id, variant, actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuditNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return Response(content=body, media_type="application/pdf")


@router.post("/{case_id}/contact-log")
async def append_disclosure_contact(
    case_id: str,
    request: DisclosureContactLogRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.append_disclosure_contact(case_id, request, actor)
    except AuditNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{case_id}/approve", response_model=DisclosurePacketResponse)
async def approve_disclosure_packet(
    case_id: str,
    request: DisclosurePacketActionRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.approve_disclosure_packet(case_id, request, actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuditNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{case_id}/manual-sent", response_model=DisclosurePacketResponse)
async def mark_disclosure_manually_sent(
    case_id: str,
    request: DisclosureManualSentRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.mark_disclosure_manually_sent(case_id, request, actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuditNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{case_id}/needs-review", response_model=DisclosurePacketResponse)
async def request_more_disclosure_review(
    case_id: str,
    request: DisclosurePacketActionRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.request_more_disclosure_review(case_id, request, actor)
    except AuditNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{case_id}/dismiss", response_model=DisclosurePacketResponse)
async def dismiss_disclosure_packet(
    case_id: str,
    request: DisclosurePacketActionRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.dismiss_disclosure_packet(case_id, request, actor)
    except AuditNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{case_id}/advance")
async def advance_disclosure_case(
    case_id: str,
    request: DisclosureAdvanceRequest,
    actor: AuthContext = Depends(get_optional_auth),
):
    try:
        return service.advance_disclosure_case(case_id, request, actor)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except AuditNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AuditAccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
