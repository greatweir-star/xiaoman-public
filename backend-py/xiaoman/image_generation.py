"""每日形象生图 — 环境变量 stub；可选 OpenAI 兼容 images API"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

ENV_HOOK = "DAILY_AVATAR_IMAGE_HOOK"
ENV_API = "DAILY_AVATAR_IMAGE_API_URL"
ENV_KEY = "XIAOMAN_IMAGE_API_KEY"
ENV_KEY_ALT = "DAILY_AVATAR_IMAGE_API_KEY"
ENV_URL_ALT = "XIAOMAN_IMAGE_API_URL"


def resolve_image_hook() -> str:
    """静态 URL 覆盖：xiaoman.json dailyAvatar.imageApiHook 或环境变量。"""
    hook = (os.environ.get(ENV_HOOK) or "").strip()
    if hook:
        return hook
    try:
        from xiaoman.dialogue.config import load_dialogue_config

        hook = str(
            load_dialogue_config().get("dailyAvatar", {}).get("imageApiHook") or ""
        ).strip()
    except Exception:
        pass
    return hook


def resolve_image_api_key() -> str:
    return (
        os.environ.get(ENV_KEY) or os.environ.get(ENV_KEY_ALT) or ""
    ).strip()


def resolve_image_api_base() -> str:
    return (
        os.environ.get(ENV_API) or os.environ.get(ENV_URL_ALT) or ""
    ).strip().rstrip("/")


def image_generation_configured() -> bool:
    hook = resolve_image_hook()
    if hook.startswith("http"):
        return True
    return bool(resolve_image_api_base() and resolve_image_api_key())


def build_generation_request(
    *,
    style: str,
    day: str,
    user_id: str = "",
    variant_id: str = "",
) -> dict[str, Any]:
    """占位请求体 — 对接真实生图服务时沿用此结构 POST。"""
    return {
        "style": style,
        "date": day,
        "user_id": user_id,
        "variant_id": variant_id,
        "prompt_hint": f"xiaoman daily outfit, style={style}",
    }


def _images_endpoint(api_base: str) -> str:
    base = api_base.rstrip("/")
    if base.endswith("/images/generations"):
        return base
    return f"{base}/images/generations"


def _call_openai_compatible_images(
    *,
    api_base: str,
    api_key: str,
    prompt: str,
    timeout: float = 30.0,
) -> str | None:
    """POST OpenAI 兼容 images/generations，返回首张 url。"""
    url = _images_endpoint(api_base)
    body = json.dumps(
        {
            "model": os.environ.get("XIAOMAN_IMAGE_MODEL", "dall-e-3"),
            "prompt": prompt,
            "n": 1,
            "size": os.environ.get("XIAOMAN_IMAGE_SIZE", "1024x1024"),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.warning("image API HTTP %s: %s", e.code, e.read()[:200])
        return None
    except Exception as e:
        logger.warning("image API request failed: %s", e)
        return None

    data = payload.get("data") if isinstance(payload, dict) else None
    if not data or not isinstance(data, list):
        return None
    first = data[0] if data else {}
    if isinstance(first, dict) and first.get("url"):
        return str(first["url"])
    return None


def fetch_generated_image_url(
    *,
    style: str,
    day: str,
    user_id: str = "",
    variant_id: str = "",
) -> str | None:
    """
    返回生图 URL；无配置或请求失败时返回 None（调用方回退静态 SVG）。

    - DAILY_AVATAR_IMAGE_HOOK=http(s)://... → 直接当作当日图 URL（MVP 接 CDN）
    - DAILY_AVATAR_IMAGE_API_URL + XIAOMAN_IMAGE_API_KEY → OpenAI 兼容 POST
    """
    hook = resolve_image_hook()
    if hook.startswith("http"):
        return hook

    api_base = resolve_image_api_base()
    api_key = resolve_image_api_key()
    if not api_base:
        return None

    params = build_generation_request(
        style=style,
        day=day,
        user_id=user_id,
        variant_id=variant_id,
    )
    prompt = str(params.get("prompt_hint") or "xiaoman companion portrait")

    if api_key:
        url = _call_openai_compatible_images(
            api_base=api_base,
            api_key=api_key,
            prompt=prompt,
        )
        if url:
            return url
        logger.debug("image API returned no url, falling back to static avatar")

    # 无密钥：仅记录 stub 查询串，便于本地 mock 网关
    query = urlencode({k: str(v) for k, v in params.items() if v})
    stub_url = f"{api_base}/generate?{query}"
    logger.debug("daily image API stub (no remote call): %s", stub_url)
    return None
