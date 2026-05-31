"""life_log.jsonl 模块测试"""

import os
import shutil

import pytest

from xiaoman.life_log import append_log, list_logs, log_path, mirror_timeline_entry
from xiaoman.life_timeline import append_event


@pytest.fixture
def log_user(tmp_path, monkeypatch):
    monkeypatch.setattr("xiaoman.life_log.DATA_DIR", str(tmp_path))
    monkeypatch.setattr("xiaoman.life_timeline.DATA_DIR", str(tmp_path))
    user_id = "life_log_test_user"
    yield user_id
    user_dir = os.path.join(tmp_path, "users", user_id)
    if os.path.isdir(user_dir):
        shutil.rmtree(user_dir, ignore_errors=True)


def test_append_and_list(log_user):
    append_log(log_user, "chat", "聊天 · 你好", source="timeline", detail="嗨")
    entries = list_logs(log_user, limit=10)
    assert len(entries) == 1
    assert entries[0]["event_type"] == "chat"
    assert os.path.isfile(log_path(log_user))


def test_timeline_mirrors_to_life_log(log_user):
    entry = append_event(log_user, "period", "进入上课时段", detail="class")
    mirror_timeline_entry(log_user, entry)
    entries = list_logs(log_user, limit=10)
    assert len(entries) >= 1
    assert any(e.get("source") == "timeline" for e in entries)
