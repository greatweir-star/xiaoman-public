"""Daily avatar metadata from configured static assets plus optional image-generation hook."""

from __future__ import annotations

import hashlib
from datetime import date

from xiaoman.image_generation import fetch_generated_image_url, image_generation_configured

DEFAULT_ASSET_ROOT = "/assets/xiaoman/avatar"
STYLE_IDS = {"fresh", "korean", "watercolor"}


def _daily_avatar_config() -> dict:
    try:
        from xiaoman.dialogue.config import load_dialogue_config

        return dict(load_dialogue_config().get("dailyAvatar") or {})
    except Exception:
        return {}


def _asset_root() -> str:
    root = str(_daily_avatar_config().get("assetRoot") or DEFAULT_ASSET_ROOT).strip()
    return root.rstrip("/") or DEFAULT_ASSET_ROOT


def _style_url(style: str) -> str:
    style_id = style if style in STYLE_IDS else "fresh"
    return f"{_asset_root()}/styles/{style_id}.png"


DAILY_VARIANTS: list[dict[str, str]] = [
    {"id": "school", "label": "\u6821\u670d\u65e5", "url": _style_url("fresh")},
    {"id": "sport", "label": "\u8fd0\u52a8\u670d\u65e5", "url": _style_url("fresh")},
    {"id": "hoodie", "label": "\u536b\u8863\u65e5", "url": _style_url("korean")},
    {"id": "cozy", "label": "\u5c45\u5bb6\u65e5", "url": _style_url("watercolor")},
    {"id": "study", "label": "\u81ea\u4e60\u65e5", "url": _style_url("fresh")},
]

STYLE_VARIANTS: dict[str, list[dict[str, str]]] = {
    "fresh": [
        {"id": "fresh-main", "label": "\u6e05\u65b0\u52a8\u753b", "url": _style_url("fresh")},
        {"id": "fresh-light", "label": "\u67d4\u548c\u5149\u7ebf", "url": _style_url("fresh")},
    ],
    "korean": [
        {"id": "korean-main", "label": "\u97e9\u7cfb\u6e05\u65b0", "url": _style_url("korean")},
        {"id": "korean-line", "label": "\u97e9\u7cfb\u7ebf\u6761", "url": _style_url("korean")},
    ],
    "watercolor": [
        {"id": "watercolor-main", "label": "\u6c34\u5f69\u6696\u8272", "url": _style_url("watercolor")},
        {"id": "watercolor-soft", "label": "\u6c34\u5f69\u5348\u540e", "url": _style_url("watercolor")},
    ],
}


def _variant_index(day: str, style: str, pool_size: int) -> int:
    """Rotate daily variants predictably so adjacent days visibly differ."""
    try:
        day_number = date.fromisoformat(day).toordinal()
    except ValueError:
        day_number = int(hashlib.sha256(day.encode()).hexdigest()[:8], 16)
    style_offset = int(hashlib.sha256(style.encode()).hexdigest()[:8], 16)
    return (day_number + style_offset) % pool_size


def resolve_daily_avatar(
    *,
    style: str = "fresh",
    day: str | None = None,
    image_api_url: str | None = None,
    user_id: str = "",
) -> dict[str, str]:
    """Return daily avatar metadata. URLs point at the configured unified avatar asset folder."""
    day = day or date.today().isoformat()
    pool = STYLE_VARIANTS.get(style) or DAILY_VARIANTS
    idx = _variant_index(day, style, len(pool))
    variant = dict(pool[idx])
    variant["date"] = day
    variant["style"] = style
    variant["assetRoot"] = _asset_root()
    variant["imageGenConfigured"] = "true" if image_generation_configured() else "false"

    generated = image_api_url
    if not generated:
        generated = fetch_generated_image_url(
            style=style,
            day=day,
            user_id=user_id,
            variant_id=variant.get("id", ""),
        )
    if generated:
        variant["generated_url"] = generated
        variant["url"] = generated
    return variant
