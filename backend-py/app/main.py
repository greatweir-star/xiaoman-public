"""V0.03 SaaS application factory shell.

The active entrypoint is still ``backend-py/main.py``. This module exists so
new SaaS routes can be introduced behind a clean application boundary before
the legacy entrypoint is retired.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.routes import router as auth_router
from app.config import get_settings
from app.data_lifecycle.routes import router as data_lifecycle_router
from app.guest_claims.routes import router as guest_claim_router
from app.tasks.routes import router as task_router
from app.usage.routes import router as usage_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Xiaoman SaaS API", version="0.3.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "env": settings.env,
            "storage": settings.storage_backend,
            "queue": settings.queue_backend,
        }

    app.include_router(auth_router)
    app.include_router(data_lifecycle_router)
    app.include_router(guest_claim_router)
    app.include_router(task_router)
    app.include_router(usage_router)
    return app


app = create_app()
