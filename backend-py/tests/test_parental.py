"""家长模式单元测试"""

from xiaoman.parental import (
    ParentalConfig,
    get_config,
    update_config,
    is_night_locked,
    check_usage_limits,
    get_usage_block_reason,
    get_usage_block_reply,
)


def test_default_config():
    cfg = ParentalConfig()
    assert cfg.enabled is False
    assert cfg.password == ""
    assert cfg.daily_limit_minutes == 60
    assert cfg.session_limit_minutes == 30
    assert cfg.crisis_resources_enabled is True


def test_get_config_missing_user():
    cfg = get_config("__test_no_user__")
    assert cfg.enabled is False


def test_update_config_first_set(tmp_path, monkeypatch):
    import xiaoman.parental as mod
    monkeypatch.setattr(mod, "DATA_DIR", str(tmp_path))
    uid = "test_u1"
    ok = update_config(uid, {"enabled": True, "password": "1234"}, "")
    assert ok is True
    cfg = get_config(uid)
    assert cfg.enabled is True
    assert cfg.password == "1234"


def test_update_config_wrong_password(tmp_path, monkeypatch):
    import xiaoman.parental as mod
    monkeypatch.setattr(mod, "DATA_DIR", str(tmp_path))
    uid = "test_u2"
    update_config(uid, {"enabled": True, "password": "1234"}, "")
    ok = update_config(uid, {"daily_limit_minutes": 90}, "0000")
    assert ok is False
    cfg = get_config(uid)
    assert cfg.daily_limit_minutes == 60  # unchanged


def test_update_config_correct_password(tmp_path, monkeypatch):
    import xiaoman.parental as mod
    monkeypatch.setattr(mod, "DATA_DIR", str(tmp_path))
    uid = "test_u3"
    update_config(uid, {"enabled": True, "password": "1234"}, "")
    ok = update_config(uid, {"daily_limit_minutes": 90}, "1234")
    assert ok is True
    cfg = get_config(uid)
    assert cfg.daily_limit_minutes == 90


def test_is_night_locked_disabled():
    assert is_night_locked("__any__") is False


def test_check_usage_limits_disabled():
    lim = check_usage_limits("__any__")
    assert lim["daily_used"] == 0
    assert lim["night_locked"] is False


def test_usage_block_reason_prefers_night_and_enforces_session():
    limits = {"night_locked": False, "daily_remaining": 10, "session_remaining": 0}
    assert get_usage_block_reason(limits) == "session"
    assert "休息" in get_usage_block_reply("session")
    limits["daily_remaining"] = 0
    assert get_usage_block_reason(limits) == "daily"
    limits["night_locked"] = True
    assert get_usage_block_reason(limits) == "night"
