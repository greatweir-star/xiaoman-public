"""新手蜜月期 — 记忆召回加成"""

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from xiaoman.honeymoon import ensure_first_seen, is_honeymoon_active, recall_top_k


@pytest.fixture
def user_dir():
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def test_ensure_first_seen_idempotent(user_dir):
    a = ensure_first_seen(user_dir)
    b = ensure_first_seen(user_dir)
    assert a == b
    path = os.path.join(user_dir, "world_meta.json")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["first_seen_at"] == a


def test_honeymoon_active_within_three_days(user_dir):
    old = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    path = os.path.join(user_dir, "world_meta.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"first_seen_at": old}, f)
    assert is_honeymoon_active(user_dir) is True
    assert recall_top_k(user_dir, default=3) == 5


def test_honeymoon_expired_after_three_days(user_dir):
    old = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
    path = os.path.join(user_dir, "world_meta.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"first_seen_at": old}, f)
    assert is_honeymoon_active(user_dir) is False
    assert recall_top_k(user_dir, default=3) == 3
