from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from wr3_api.api.routes import (
    audits,
    auth,
    billing,
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
from wr3_api.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="wr3 API",
        version="0.1.0",
        description="API MVP для ИИ-предаудита и триажа рисков смарт-контрактов.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins + ["http://localhost:3001", "http://127.0.0.1:3001"],
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(integrations.router)
    app.include_router(monitoring.router)
    app.include_router(news.router)
    app.include_router(auth.router)
    app.include_router(billing.router)
    app.include_router(audits.router)
    app.include_router(notifications.router)
    app.include_router(projects.router)
    app.include_router(disclosure.router)
    app.include_router(telegram.router)
    app.include_router(tools.router)
    return app


app = create_app()
