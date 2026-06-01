import json

from app.config import Settings
from app.data_lifecycle.service import DataLifecycleService


def test_file_data_lifecycle_exports_and_deletes_user_directory(tmp_path):
    user_id = "user-1"
    identity = tmp_path / "users" / user_id / "user" / "identity.json"
    identity.parent.mkdir(parents=True)
    identity.write_text(json.dumps({"name": "Alice"}), encoding="utf-8")
    service = DataLifecycleService(Settings(storage_backend="file"), data_dir=str(tmp_path))

    result = service.export_user_data(tenant_id="tenant-1", user_id=user_id)
    export_path = service.export_path(user_id=user_id, export_id=result["export_id"])
    payload = json.loads(export_path.read_text(encoding="utf-8"))

    assert payload["files"]["user/identity.json"] == '{"name": "Alice"}'
    assert service.delete_user_data(tenant_id="tenant-1", user_id=user_id) == 1
    assert not identity.exists()
    assert export_path.exists()


def test_export_path_is_scoped_to_user(tmp_path):
    service = DataLifecycleService(Settings(storage_backend="file"), data_dir=str(tmp_path))
    result = service.export_user_data(tenant_id="tenant-1", user_id="user-1")

    try:
        service.export_path(user_id="user-2", export_id=result["export_id"])
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("another user must not download the export")
