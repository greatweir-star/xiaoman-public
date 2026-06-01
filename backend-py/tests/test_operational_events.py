from app.config import Settings
from app.operations.service import create_operational_services


def test_file_operational_services_record_scoped_audit_and_safety_events(tmp_path):
    services = create_operational_services(Settings(storage_backend="file"), data_dir=str(tmp_path))

    services.audit.record(tenant_id="tenant-1", user_id="user-1", action="auth.login", resource="session")
    services.safety.record(
        tenant_id="tenant-1",
        user_id="user-1",
        category="self_harm",
        metadata={"resources_included": True},
    )

    audit_rows = services.audit.repository.list_for_user("tenant-1", "user-1")
    safety_rows = services.safety.repository.list_for_user("tenant-1", "user-1")
    assert audit_rows[0]["action"] == "auth.login"
    assert safety_rows[0]["category"] == "self_harm"
    assert "message" not in safety_rows[0]["metadata"]
