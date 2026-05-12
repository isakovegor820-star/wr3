from __future__ import annotations

from wr3_api.core.config import get_settings


def create_celery_app():
    try:
        from celery import Celery
    except ImportError as exc:  # pragma: no cover - depends on production extras
        raise RuntimeError("celery is not installed; install wr3-api worker extras") from exc

    settings = get_settings()
    app = Celery(
        "wr3",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=["wr3_api.workers.tasks"],
    )
    app.conf.update(
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_default_queue="audit_jobs",
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        beat_schedule={
            "wr3-retention-sweep-daily": {
                "task": "wr3.retention_sweep",
                "schedule": 86_400.0,
                "args": (False,),
            }
        },
    )
    return app


celery_app = create_celery_app()
