"""每日形象生图 stub"""

from xiaoman.daily_avatar import resolve_daily_avatar
from xiaoman.image_generation import (
    _call_openai_compatible_images,
    build_generation_request,
    fetch_generated_image_url,
    image_generation_configured,
    resolve_image_api_key,
    resolve_image_hook,
)


def test_build_generation_request_shape():
    body = build_generation_request(style="fresh", day="2026-05-27", user_id="u1")
    assert body["style"] == "fresh"
    assert "prompt_hint" in body


def test_hook_url_overrides_avatar(monkeypatch):
    monkeypatch.setenv("DAILY_AVATAR_IMAGE_HOOK", "https://cdn.example/xiaoman-today.png")
    monkeypatch.delenv("DAILY_AVATAR_IMAGE_API_URL", raising=False)
    assert image_generation_configured()
    assert resolve_image_hook().startswith("https://")
    meta = resolve_daily_avatar(style="fresh", day="2026-05-27")
    assert meta["url"] == "https://cdn.example/xiaoman-today.png"


def test_api_stub_returns_none_without_remote(monkeypatch):
    monkeypatch.delenv("DAILY_AVATAR_IMAGE_HOOK", raising=False)
    monkeypatch.setenv("DAILY_AVATAR_IMAGE_API_URL", "https://api.example/v1/avatar")
    monkeypatch.delenv("XIAOMAN_IMAGE_API_KEY", raising=False)
    assert fetch_generated_image_url(style="korean", day="2026-05-27") is None
    meta = resolve_daily_avatar(style="korean")
    assert meta["url"].startswith("/assets/xiaoman/avatar/styles/")


def test_image_configured_with_api_key(monkeypatch):
    monkeypatch.delenv("DAILY_AVATAR_IMAGE_HOOK", raising=False)
    monkeypatch.setenv("DAILY_AVATAR_IMAGE_API_URL", "https://api.example/v1")
    monkeypatch.setenv("XIAOMAN_IMAGE_API_KEY", "test-key")
    assert image_generation_configured()
    assert resolve_image_api_key() == "test-key"


def test_openai_compatible_images_parses_url(monkeypatch):
    class FakeResp:
        def read(self):
            return b'{"data":[{"url":"https://cdn.example/gen.png"}]}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    monkeypatch.setattr(
        "xiaoman.image_generation.urllib.request.urlopen",
        lambda *a, **k: FakeResp(),
    )
    url = _call_openai_compatible_images(
        api_base="https://api.example/v1",
        api_key="k",
        prompt="test",
    )
    assert url == "https://cdn.example/gen.png"
