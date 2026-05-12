from fastapi import APIRouter

from wr3_api.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "wr3-api"}


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "live", "service": "wr3-api"}


@router.get("/ready")
async def ready() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ready",
        "service": "wr3-api",
        "environment": settings.environment,
        "checks": {
            "storage": "postgres_configured" if settings.database_url else "in_memory_local",
            "task_backend": settings.task_backend,
            "artifact_encryption": bool(settings.artifact_encryption_key),
            "llm_provider": settings.llm_provider,
            "backup_target": "r2_configured" if settings.backup_r2_uri else "local_only",
            "sentry": "configured" if settings.sentry_dsn else "not_configured",
            "telegram_alerts": "configured" if settings.telegram_alert_chat_id else "not_configured",
        },
    }
