"""Polling worker process for PostgreSQL-backed background tasks."""

from __future__ import annotations

import logging
import os
import socket
import time
import uuid

from app.tasks.service import get_task_service
from app.workers.handlers import default_handlers
from app.security.redaction import configure_redacted_logging

logger = logging.getLogger(__name__)


def worker_id() -> str:
    return os.environ.get("XIAOMAN_WORKER_ID") or f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"


def run_forever(*, poll_seconds: float = 1.0) -> None:
    service = get_task_service()
    handlers = default_handlers()
    identity = worker_id()
    logger.info("Worker started: %s", identity)
    while True:
        task = service.run_once(worker_id=identity, handlers=handlers)
        if not task:
            time.sleep(max(poll_seconds, 0.05))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    configure_redacted_logging()
    run_forever(poll_seconds=float(os.environ.get("XIAOMAN_WORKER_POLL_SECONDS", "1")))
