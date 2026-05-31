"""生活时间线模块测试"""

import os
import shutil

import pytest

from xiaoman.life_timeline import (
    append_event,
    list_events,
    record_period_if_changed,
    timeline_path,
)


@pytest.fixture
def timeline_user(tmp_path, monkeypatch):
    monkeypatch.setattr("xiaoman.life_timeline.DATA_DIR", str(tmp_path))
    user_id = "timeline_test_user"
    yield user_id
    user_dir = os.path.join(tmp_path, "users", user_id)
    if os.path.isdir(user_dir):
        shutil.rmtree(user_dir, ignore_errors=True)


def test_append_and_list_sorted(timeline_user):
    append_event(timeline_user, "chat", "聊天 · 你好", detail="嗨")
    append_event(timeline_user, "diary", "写了今日日记", detail="今天：上课")
    entries = list_events(timeline_user, limit=10)
    assert len(entries) == 2
    assert entries[0]["ts"] >= entries[1]["ts"]
    assert os.path.isfile(timeline_path(timeline_user))


def test_period_dedup(timeline_user):
    first = record_period_if_changed(timeline_user, "class")
    second = record_period_if_changed(timeline_user, "class")
    assert first is not None
    assert second is None
    changed = record_period_if_changed(timeline_user, "lunch")
    assert changed is not None
    types = [e["type"] for e in list_events(timeline_user)]
    assert types.count("period") == 2
