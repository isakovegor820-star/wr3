from __future__ import annotations

import asyncio
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


def dispatch_audit_processing_detached(
    *,
    audit_id: UUID,
    local_processor: LocalProcessor,
) -> tuple[list[str], asyncio.Task[None] | None]:
    """Dispatch processing from a non-HTTP context (e.g. the scout autopilot loop,
    which has no FastAPI BackgroundTasks). Uses Celery when configured so queued
    work survives an API restart; otherwise schedules an in-process asyncio task.

    Returns the dispatch limitations and the local task (None when handed to Celery)
    so callers can track in-process work.
    """
    settings = get_settings()
    if settings.task_backend == "celery":
        try:
            from wr3_api.workers.tasks import process_audit_task

            process_audit_task.delay(str(audit_id))
            return ["celery_dispatcher_enqueued"], None
        except Exception:
            pass
    task = asyncio.create_task(local_processor(audit_id))
    return ["local_inprocess_task_scheduled"], task
