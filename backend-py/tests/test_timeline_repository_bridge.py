from xiaoman import life_timeline


class MemoryTimelineRepository:
    def __init__(self):
        self.rows = []

    def append_event(self, tenant_id, user_id, companion_id, event):
        self.rows.append({**event, "tenant_id": tenant_id, "user_id": user_id, "companion_id": companion_id})

    def list_events(self, tenant_id, user_id, companion_id, limit=80):
        return [
            {
                "id": row["id"],
                "type": row["type"],
                "title": row["title"],
                "detail": row["detail"],
                "metadata": {"ts": row["ts"], "meta": row.get("meta")},
            }
            for row in reversed(self.rows[-limit:])
            if row["tenant_id"] == tenant_id and row["user_id"] == user_id and row["companion_id"] == companion_id
        ]


def test_timeline_repository_bridge_dual_writes_and_reads(tmp_path, monkeypatch):
    repository = MemoryTimelineRepository()
    monkeypatch.setattr(life_timeline, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(life_timeline, "_repository", None)
    life_timeline.configure_timeline_repository(repository, tenant_id="tenant-1")

    entry = life_timeline.append_event("user-1", "chat", "hello", meta={"emotion": "温柔"})

    assert repository.rows[0]["id"] == entry["id"]
    assert life_timeline.list_events("user-1") == [entry]
