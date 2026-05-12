from uuid import uuid4

from fastapi import BackgroundTasks

from wr3_api.core.config import get_settings
from wr3_api.services.dispatcher import dispatch_audit_processing


async def noop_processor(_audit_id):
    return None


def test_dispatcher_enqueues_local_background_task():
    settings = get_settings()
    original = settings.task_backend
    settings.task_backend = "local"
    try:
        background_tasks = BackgroundTasks()
        limitations = dispatch_audit_processing(
            audit_id=uuid4(),
            background_tasks=background_tasks,
            local_processor=noop_processor,
        )

        assert limitations == ["local_background_dispatcher_enqueued"]
        assert len(background_tasks.tasks) == 1
    finally:
        settings.task_backend = original


def test_dispatcher_falls_back_for_unknown_backend():
    settings = get_settings()
    original = settings.task_backend
    settings.task_backend = "not-real"
    try:
        background_tasks = BackgroundTasks()
        limitations = dispatch_audit_processing(
            audit_id=uuid4(),
            background_tasks=background_tasks,
            local_processor=noop_processor,
        )

        assert limitations == ["unknown_task_backend_not-real_fell_back_to_local_background"]
        assert len(background_tasks.tasks) == 1
    finally:
        settings.task_backend = original


def test_dispatcher_falls_back_when_celery_extra_missing():
    settings = get_settings()
    original = settings.task_backend
    settings.task_backend = "celery"
    try:
        background_tasks = BackgroundTasks()
        limitations = dispatch_audit_processing(
            audit_id=uuid4(),
            background_tasks=background_tasks,
            local_processor=noop_processor,
        )

        assert limitations in (
            ["celery_dispatcher_enqueued"],
            ["celery_dispatcher_unavailable_fell_back_to_local_background"],
        )
        if limitations[0].endswith("local_background"):
            assert len(background_tasks.tasks) == 1
    finally:
        settings.task_backend = original
