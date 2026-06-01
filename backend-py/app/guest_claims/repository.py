"""File-backed guest claim state for local mode and migration testing."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from psycopg import connect
from psycopg.rows import dict_row

from app.config import Settings, get_settings
from xiaoman.paths import DATA_DIR


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


class GuestClaimRepository(Protocol):
    def save_token(self, *, tenant_id: str, guest_id: str, token_hash: str, expires_at: datetime) -> None:
        ...

    def reserve_token(self, *, tenant_id: str, guest_id: str, token_hash: str) -> None:
        ...

    def get_claim(self, *, tenant_id: str, guest_id: str) -> dict[str, Any] | None:
        ...

    def begin_claim(self, *, tenant_id: str, guest_id: str, user_id: str, token_hash: str) -> dict[str, Any]:
        ...

    def complete_claim(self, *, tenant_id: str, guest_id: str, archive_path: str) -> dict[str, Any]:
        ...

    def fail_claim(self, *, tenant_id: str, guest_id: str, error_message: str) -> dict[str, Any]:
        ...


class FileGuestClaimRepository:
    """Persist claim state atomically so retries survive process restarts."""

    def __init__(self, data_dir: str = DATA_DIR) -> None:
        self.path = Path(data_dir) / "guest_claims.json"
        self._lock = threading.Lock()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"tokens": {}, "claims": {}}
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
        os.replace(temp_path, self.path)

    def save_token(self, *, tenant_id: str, guest_id: str, token_hash: str, expires_at: datetime) -> None:
        with self._lock:
            state = self._load()
            state["tokens"][token_hash] = {
                "tenant_id": tenant_id,
                "guest_id": guest_id,
                "expires_at": _iso(expires_at),
                "created_at": _iso(),
                "used_at": None,
            }
            self._save(state)

    def reserve_token(self, *, tenant_id: str, guest_id: str, token_hash: str) -> None:
        with self._lock:
            state = self._load()
            token = state["tokens"].get(token_hash)
            if not token or token["tenant_id"] != tenant_id or token["guest_id"] != guest_id:
                raise ValueError("claim token not found")
            if token.get("used_at"):
                raise ValueError("claim token already used")
            expires_at = datetime.fromisoformat(token["expires_at"])
            if expires_at < _now():
                raise ValueError("claim token expired")
            token["used_at"] = _iso()
            self._save(state)

    def get_claim(self, *, tenant_id: str, guest_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._load()["claims"].get(f"{tenant_id}:{guest_id}")

    def begin_claim(self, *, tenant_id: str, guest_id: str, user_id: str, token_hash: str) -> dict[str, Any]:
        with self._lock:
            state = self._load()
            key = f"{tenant_id}:{guest_id}"
            claim = state["claims"].get(key)
            if claim and claim["user_id"] != user_id:
                raise ValueError("guest data already claimed by another account")
            if not claim:
                claim = {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "guest_id": guest_id,
                    "user_id": user_id,
                    "requested_at": _iso(),
                }
            claim.update(
                {
                    "status": "pending",
                    "claim_token_hash": token_hash,
                    "completed_at": None,
                    "error_message": None,
                }
            )
            state["claims"][key] = claim
            self._save(state)
            return claim

    def complete_claim(self, *, tenant_id: str, guest_id: str, archive_path: str) -> dict[str, Any]:
        return self._update_claim(
            tenant_id=tenant_id,
            guest_id=guest_id,
            status="completed",
            completed_at=_iso(),
            archive_path=archive_path,
            error_message=None,
        )

    def fail_claim(self, *, tenant_id: str, guest_id: str, error_message: str) -> dict[str, Any]:
        return self._update_claim(
            tenant_id=tenant_id,
            guest_id=guest_id,
            status="failed",
            error_message=error_message[:500],
        )

    def _update_claim(self, *, tenant_id: str, guest_id: str, status: str, **updates: Any) -> dict[str, Any]:
        with self._lock:
            state = self._load()
            key = f"{tenant_id}:{guest_id}"
            claim = state["claims"][key]
            claim.update({"status": status, **updates})
            self._save(state)
            return claim


class PostgresGuestClaimRepository:
    """Share claim token and migration state across SaaS instances."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _connect(self):
        return connect(self.database_url, row_factory=dict_row)

    def save_token(self, *, tenant_id: str, guest_id: str, token_hash: str, expires_at: datetime) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO tenants (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (tenant_id, tenant_id),
            )
            cursor.execute(
                """
                INSERT INTO guest_claim_tokens (token_hash, tenant_id, guest_id, expires_at)
                VALUES (%s, %s, %s, %s)
                """,
                (token_hash, tenant_id, guest_id, expires_at),
            )

    def reserve_token(self, *, tenant_id: str, guest_id: str, token_hash: str) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE guest_claim_tokens
                SET used_at = now()
                WHERE token_hash = %s AND tenant_id = %s AND guest_id = %s
                  AND used_at IS NULL AND expires_at >= now()
                RETURNING token_hash
                """,
                (token_hash, tenant_id, guest_id),
            )
            if not cursor.fetchone():
                raise ValueError("claim token missing, expired, or already used")

    def get_claim(self, *, tenant_id: str, guest_id: str) -> dict[str, Any] | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM guest_claims WHERE tenant_id = %s AND guest_id = %s",
                (tenant_id, guest_id),
            )
            return cursor.fetchone()

    def begin_claim(self, *, tenant_id: str, guest_id: str, user_id: str, token_hash: str) -> dict[str, Any]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM guest_claims
                WHERE tenant_id = %s AND guest_id = %s
                FOR UPDATE
                """,
                (tenant_id, guest_id),
            )
            claim = cursor.fetchone()
            if claim and claim["user_id"] != user_id:
                raise ValueError("guest data already claimed by another account")
            if claim:
                cursor.execute(
                    """
                    UPDATE guest_claims
                    SET status = 'pending', claim_token_hash = %s, completed_at = NULL, error_message = NULL
                    WHERE tenant_id = %s AND guest_id = %s
                    RETURNING *
                    """,
                    (token_hash, tenant_id, guest_id),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO guest_claims (id, tenant_id, guest_id, user_id, status, claim_token_hash)
                    VALUES (%s, %s, %s, %s, 'pending', %s)
                    RETURNING *
                    """,
                    (str(uuid.uuid4()), tenant_id, guest_id, user_id, token_hash),
                )
            return cursor.fetchone()

    def complete_claim(self, *, tenant_id: str, guest_id: str, archive_path: str) -> dict[str, Any]:
        return self._update_claim(
            tenant_id=tenant_id,
            guest_id=guest_id,
            status="completed",
            completed_at=_now(),
            archive_path=archive_path,
            error_message=None,
        )

    def fail_claim(self, *, tenant_id: str, guest_id: str, error_message: str) -> dict[str, Any]:
        return self._update_claim(
            tenant_id=tenant_id,
            guest_id=guest_id,
            status="failed",
            error_message=error_message[:500],
        )

    def _update_claim(self, *, tenant_id: str, guest_id: str, status: str, **updates: Any) -> dict[str, Any]:
        assignments = ["status = %s"]
        values: list[Any] = [status]
        for column, value in updates.items():
            assignments.append(f"{column} = %s")
            values.append(value)
        values.extend([tenant_id, guest_id])
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE guest_claims
                SET {", ".join(assignments)}
                WHERE tenant_id = %s AND guest_id = %s
                RETURNING *
                """,
                values,
            )
            return cursor.fetchone()


def create_guest_claim_repository(settings: Settings | None = None) -> GuestClaimRepository:
    runtime_settings = settings or get_settings()
    if runtime_settings.uses_postgres:
        if not runtime_settings.database_url:
            raise RuntimeError("DATABASE_URL is required when XIAOMAN_STORAGE_BACKEND=postgres")
        return PostgresGuestClaimRepository(runtime_settings.database_url)
    return FileGuestClaimRepository()
