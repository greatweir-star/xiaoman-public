import json
import uuid

from fastapi import HTTPException

from app.auth.repository import AuthUser
from app.config import Settings
from app.guest_claims.migration import FileGuestMigrator, validate_uuid
from app.guest_claims.repository import FileGuestClaimRepository
from app.guest_claims.service import GuestClaimService


def _id() -> str:
    return str(uuid.uuid4())


def _service(tmp_path):
    return GuestClaimService(
        FileGuestClaimRepository(str(tmp_path)),
        FileGuestMigrator(str(tmp_path)),
        Settings(jwt_secret="guest-claim-test-secret"),
    )


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_validate_uuid_rejects_path_traversal():
    try:
        validate_uuid("../escape")
    except ValueError:
        pass
    else:
        raise AssertionError("guest ids must not escape the data directory")


def test_file_guest_migrator_merges_and_archives_source(tmp_path):
    guest_id = _id()
    user_id = _id()
    _write_json(tmp_path / "users" / guest_id / "user" / "identity.json", {"name": "Guest", "grade": 8})
    _write_json(tmp_path / "users" / user_id / "user" / "identity.json", {"name": "Formal"})
    _write_json(
        tmp_path / "sessions" / f"{guest_id}.json",
        {"user_id": guest_id, "messages": [{"kind": "user", "payload": {"content": "guest hello"}}]},
    )
    _write_json(
        tmp_path / "sessions" / f"{user_id}.json",
        {"user_id": user_id, "messages": [{"kind": "user", "payload": {"content": "formal hello"}}]},
    )

    result = FileGuestMigrator(str(tmp_path)).migrate(guest_id=guest_id, user_id=user_id)

    identity = json.loads((tmp_path / "users" / user_id / "user" / "identity.json").read_text(encoding="utf-8"))
    session = json.loads((tmp_path / "sessions" / f"{user_id}.json").read_text(encoding="utf-8"))
    assert identity == {"name": "Formal", "grade": 8}
    assert [row["payload"]["content"] for row in session["messages"]] == ["formal hello", "guest hello"]
    assert not (tmp_path / "users" / guest_id).exists()
    assert (tmp_path / "guest_archive" / guest_id).exists()
    assert result["status"] == "completed"


def test_file_guest_migrator_dry_run_does_not_move_data(tmp_path):
    guest_id = _id()
    user_id = _id()
    _write_json(tmp_path / "users" / guest_id / "user" / "identity.json", {"name": "Guest"})

    result = FileGuestMigrator(str(tmp_path)).migrate(guest_id=guest_id, user_id=user_id, dry_run=True)

    assert result["status"] == "dry_run"
    assert (tmp_path / "users" / guest_id).exists()
    assert not (tmp_path / "users" / user_id).exists()


def test_guest_claim_service_is_idempotent_and_rejects_other_account(tmp_path):
    guest_id = _id()
    user = AuthUser(id=_id(), tenant_id="default", email="first@example.com", password_hash="hash")
    other_user = AuthUser(id=_id(), tenant_id="default", email="second@example.com", password_hash="hash")
    _write_json(tmp_path / "users" / guest_id / "user" / "identity.json", {"name": "Guest"})
    service = _service(tmp_path)

    token = service.issue_token(guest_id)["claim_token"]
    claimed = service.claim(guest_id=guest_id, claim_token=str(token), user=user)
    repeated = service.claim(guest_id=guest_id, claim_token=str(token), user=user)

    assert claimed["status"] == "completed"
    assert repeated == claimed

    try:
        service.claim(guest_id=guest_id, claim_token=str(token), user=other_user)
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("a completed guest claim must not be rebound")


def test_guest_claim_service_requires_existing_guest_data(tmp_path):
    try:
        _service(tmp_path).issue_token(_id())
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("claim token must not be issued without guest data")
