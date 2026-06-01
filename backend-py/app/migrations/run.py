"""Apply ordered SQL migrations when DATABASE_URL is configured."""

from __future__ import annotations

import logging
from pathlib import Path

from psycopg import connect

from app.config import get_settings

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    settings = get_settings()
    if not settings.database_url:
        logger.info("DATABASE_URL is unset; skipping SQL migrations")
        return

    migrations_dir = Path(__file__).parent
    with connect(settings.database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        for path in sorted(migrations_dir.glob("*.sql")):
            cursor.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (path.name,))
            if cursor.fetchone():
                continue
            cursor.execute(path.read_text(encoding="utf-8-sig"))
            cursor.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,))
            logger.info("Applied migration %s", path.name)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()
