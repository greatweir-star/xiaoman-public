"""V0.03 SaaS application factory shell.

The active entrypoint is still ``backend-py/main.py``. This module exists so
new SaaS routes can be introduced behind a clean application boundary before
the legacy entrypoint is retired.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.auth.routes import router as auth_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Xiaoman SaaS API", version="0.3.0")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "env": settings.env,
            "storage": settings.storage_backend,
            "queue": settings.queue_backend,
        }

    app.include_router(auth_router)
    return app


app = create_app()
