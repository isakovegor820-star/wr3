from fastapi import APIRouter, Depends, HTTPException

from wr3_api.api.dependencies import get_optional_auth
from wr3_api.api.routes.audits import service
from wr3_api.domain.schemas import DisclosureAdvanceRequest, DisclosureCaseRequest, DisclosureContactLogRequest
from wr3_api.services.audit_service import AuditAccessDenied, AuditNotFound
from wr3_api.services.auth import AuthContext

router = APIRouter(prefix="/v1/disclosure-cases", tags=["disclosure"])


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
