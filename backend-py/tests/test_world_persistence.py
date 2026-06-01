import json

from app.services.world_persistence import WorldPersistenceService


class MemoryWorldRepository:
    def __init__(self):
        self.layers = {}

    def load_layer(self, tenant_id, user_id, companion_id, side, layer):
        return self.layers.get((tenant_id, user_id, companion_id, side, layer), {})

    def save_layer(self, tenant_id, user_id, companion_id, side, layer, data):
        self.layers[(tenant_id, user_id, companion_id, side, layer)] = data


def test_world_persistence_sync_and_hydrate_roundtrip(tmp_path):
    repository = MemoryWorldRepository()
    service = WorldPersistenceService(repository, tenant_id="tenant-1")
    root = tmp_path / "users" / "user-1"
    identity = root / "user" / "identity.json"
    identity.parent.mkdir(parents=True)
    identity.write_text(json.dumps({"name": "Alice"}), encoding="utf-8")

    assert service.sync(user_id="user-1", user_data_dir=str(root)) == 1

    identity.unlink()
    assert service.hydrate(user_id="user-1", user_data_dir=str(root)) == 1
    assert json.loads(identity.read_text(encoding="utf-8")) == {"name": "Alice"}
