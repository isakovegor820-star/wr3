import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wr3_api.api.routes import (
    audits,
    auth,
    disclosure,
    health,
    integrations,
    monitoring,
    news,
    notifications,
    projects,
    telegram,
    tools,
)
from wr3_api.core.config import Settings, get_settings
from wr3_api.services.repository import close_all_pools

_WILDCARD = {"*", ".*", ".+"}


def _safe_cors(settings: Settings) -> tuple[list[str], str | None]:
    """Build a credentialed-safe CORS allowlist.

    ``allow_credentials=True`` with a wildcard origin is both rejected by browsers
    and a real CSRF/exfiltration risk, so we strip any ``*`` origin (and wildcard
    regex) rather than silently shipping an unsafe combination. Cross-origin
    callers must be named explicitly.
    """
    base = [*settings.cors_origins, "http://localhost:3001", "http://127.0.0.1:3001"]
    origins = [origin for origin in dict.fromkeys(base) if origin and origin not in _WILDCARD]
    regex = settings.cors_origin_regex if settings.cors_origin_regex not in _WILDCARD else None
    return origins, regex


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if settings.scout_autopilot_enabled:
            await monitoring.scout_autopilot.start()
        bot_task: asyncio.Task[None] | None = None
        if settings.telegram_bot_token and settings.telegram_reviewer_user_ids:
            from wr3_api.services.telegram_bot import TelegramCommandBot

            bot = TelegramCommandBot(
                audit_service=monitoring.audit_service,
                scout_autopilot=monitoring.scout_autopilot,
                settings=settings,
            )
            bot_task = asyncio.create_task(bot.run(), name="wr3-telegram-bot")
        try:
            yield
        finally:
            if bot_task is not None:
                bot_task.cancel()
                try:
                    await bot_task
                except asyncio.CancelledError:
                    pass
            await monitoring.scout_autopilot.stop()
            close_all_pools()

    app = FastAPI(
        title="wr3 API",
        version="0.1.0",
        description="API MVP для ИИ-предаудита и триажа рисков смарт-контрактов.",
        lifespan=lifespan,
    )
    cors_origins, cors_regex = _safe_cors(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=cors_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(integrations.router)
    app.include_router(monitoring.router)
    app.include_router(news.router)
    app.include_router(auth.router)
    app.include_router(audits.router)
    app.include_router(notifications.router)
    app.include_router(projects.router)
    app.include_router(disclosure.router)
    app.include_router(telegram.router)
    app.include_router(tools.router)
    return app


app = create_app()
