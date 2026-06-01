from app.repositories.file import create_file_repositories


def test_file_session_repository_roundtrip(tmp_path):
    repositories = create_file_repositories(str(tmp_path))
    session_id = repositories.sessions.create_session("tenant-1", "user-1", "xiaoman")

    repositories.sessions.append_message(session_id, {"role": "user", "content": "hello"})

    assert repositories.sessions.load_messages(session_id) == [
        {"type": "message", "role": "user", "content": "hello"}
    ]


def test_file_session_repository_reuses_scoped_session(tmp_path):
    repositories = create_file_repositories(str(tmp_path))

    first = repositories.sessions.get_or_create_session("tenant-1", "user-1", "xiaoman")
    second = repositories.sessions.get_or_create_session("tenant-1", "user-1", "xiaoman")

    assert second == first


def test_file_world_repository_roundtrip(tmp_path):
    repositories = create_file_repositories(str(tmp_path))

    repositories.world.save_layer("tenant-1", "user-1", "xiaoman", "user", "l1", {"name": "Alice"})

    assert repositories.world.load_layer("tenant-1", "user-1", "xiaoman", "user", "l1") == {"name": "Alice"}


def test_file_memory_repository_deduplicates_and_searches(tmp_path):
    repositories = create_file_repositories(str(tmp_path))

    assert repositories.memory.save_fact("tenant-1", "user-1", "xiaoman", {"fact": "likes music"})
    assert not repositories.memory.save_fact("tenant-1", "user-1", "xiaoman", {"fact": "likes music"})
    assert repositories.memory.search("tenant-1", "user-1", "xiaoman", "music", 5)[0]["fact"] == "likes music"


def test_file_timeline_repository_sorts_newest_first(tmp_path):
    repositories = create_file_repositories(str(tmp_path))

    repositories.timeline.append_event("tenant-1", "user-1", "xiaoman", {"ts": "2026-05-30", "title": "old"})
    repositories.timeline.append_event("tenant-1", "user-1", "xiaoman", {"ts": "2026-05-31", "title": "new"})

    assert [row["title"] for row in repositories.timeline.list_events("tenant-1", "user-1", "xiaoman")] == [
        "new",
        "old",
    ]


def test_file_repository_rejects_path_traversal(tmp_path):
    repositories = create_file_repositories(str(tmp_path))

    try:
        repositories.world.save_layer("tenant-1", "../user", "xiaoman", "user", "l1", {})
    except ValueError:
        pass
    else:
        raise AssertionError("repository keys must not escape the storage root")
