import json

from scripts.migrate_file_to_postgres import summarize_data


def test_migration_inventory_counts_uuid_users_and_hashes_files(tmp_path):
    user_id = "11221ab9-2f4f-4cac-94a7-75c63234ed18"
    identity = tmp_path / "users" / user_id / "user" / "identity.json"
    identity.parent.mkdir(parents=True)
    identity.write_text(json.dumps({"name": "Alice"}), encoding="utf-8")
    ignored = tmp_path / "users" / "test-user"
    ignored.mkdir(parents=True)

    summary = summarize_data(str(tmp_path))

    assert summary["mode"] == "dry-run"
    assert summary["counts"]["users"] == 1
    assert summary["counts"]["world_files"] == 1
    assert summary["counts"]["hashed_files"] == 1
    assert summary["samples"][user_id]["world"] == [f"users/{user_id}/user/identity.json"]
    assert summary["skipped_non_uuid_user_dirs"] == ["test-user"]
    assert len(next(iter(summary["hashes"].values()))) == 64
