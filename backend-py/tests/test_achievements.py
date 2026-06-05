"""Achievement unlock regression tests."""

from xiaoman import achievements


def test_check_achievements_persists_new_unlock_once(tmp_path, monkeypatch):
    monkeypatch.setattr(achievements, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(achievements, "timeline_list", lambda user_id, limit=500: [])
    monkeypatch.setattr(achievements, "_check_first_vent", lambda timeline: True)

    first = achievements.check_achievements("achievement-user")
    second = achievements.check_achievements("achievement-user")

    assert [item["id"] for item in first] == ["first_vent"]
    assert second == []
