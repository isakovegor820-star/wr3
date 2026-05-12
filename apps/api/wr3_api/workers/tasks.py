from __future__ import annotations

import asyncio
from uuid import UUID

from wr3_api.services.audit_service import AuditService
from wr3_api.workers.celery_app import celery_app


@celery_app.task(name="wr3.process_audit")
def process_audit_task(audit_id: str) -> dict[str, str]:
    service = AuditService()
    asyncio.run(service.process_audit(UUID(audit_id)))
    return {"audit_id": audit_id, "status": "processed"}


@celery_app.task(name="wr3.retention_sweep")
def retention_sweep_task(dry_run: bool = False) -> dict[str, object]:
    service = AuditService()
    result = service.run_retention_sweep(dry_run=dry_run)
    return result.__dict__
