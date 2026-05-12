from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import BackgroundTasks

from wr3_api.core.config import get_settings


LocalProcessor = Callable[[UUID], Awaitable[None]]


def dispatch_audit_processing(
    *,
    audit_id: UUID,
    background_tasks: BackgroundTasks,
    local_processor: LocalProcessor,
) -> list[str]:
    settings = get_settings()
    if settings.task_backend == "local":
        background_tasks.add_task(local_processor, audit_id)
        return ["local_background_dispatcher_enqueued"]

    if settings.task_backend == "celery":
        try:
            from wr3_api.workers.tasks import process_audit_task

            process_audit_task.delay(str(audit_id))
            return ["celery_dispatcher_enqueued"]
        except Exception:
            background_tasks.add_task(local_processor, audit_id)
            return ["celery_dispatcher_unavailable_fell_back_to_local_background"]

    background_tasks.add_task(local_processor, audit_id)
    return [f"unknown_task_backend_{settings.task_backend}_fell_back_to_local_background"]
