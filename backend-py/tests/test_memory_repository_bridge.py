from xiaoman.memory.store import MemoryStore


class MemoryFactRepository:
    def __init__(self):
        self.rows = []

    def save_fact(self, tenant_id, user_id, companion_id, fact):
        self.rows.append({**fact, "tenant_id": tenant_id, "user_id": user_id, "companion_id": companion_id})
        return True

    def search(self, tenant_id, user_id, companion_id, query, top_k):
        return [
            row
            for row in self.rows
            if row["tenant_id"] == tenant_id and row["user_id"] == user_id and row["companion_id"] == companion_id
        ][:top_k]


def test_memory_store_dual_writes_and_reads_repository_facts(tmp_path):
    repository = MemoryFactRepository()
    store = MemoryStore(str(tmp_path), fact_repository=repository, tenant_id="tenant-1")

    assert store.save_fact("user-1", "likes music", "preference", "L7")
    assert repository.rows[0]["fact"] == "likes music"

    fresh_store = MemoryStore(str(tmp_path / "fresh"), fact_repository=repository, tenant_id="tenant-1")
    assert fresh_store.load_facts("user-1")[0]["fact"] == "likes music"
