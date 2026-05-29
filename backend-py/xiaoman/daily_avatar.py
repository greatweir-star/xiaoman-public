"""每日形象 MVP — 按日期/画风轮换静态资源，预留生图 hook"""

from __future__ import annotations

import hashlib
from datetime import date

from xiaoman.image_generation import fetch_generated_image_url, image_generation_configured

# 设定形象走 /styles 与 onboarding 画风一致；/avatars 仅作聊天气泡情绪图标
def _style_url(style: str) -> str:
    if style in ("fresh", "korean", "watercolor"):
        return f"/styles/{style}.svg"
    return "/styles/fresh.svg"


DAILY_VARIANTS: list[dict[str, str]] = [
    {"id": "school", "label": "校服日", "url": "/styles/fresh.svg"},
    {"id": "sport", "label": "运动服日", "url": "/styles/fresh.svg"},
    {"id": "hoodie", "label": "卫衣日", "url": "/styles/korean.svg"},
    {"id": "cozy", "label": "居家日", "url": "/styles/watercolor.svg"},
    {"id": "study", "label": "自习日", "url": "/styles/fresh.svg"},
]

STYLE_VARIANTS: dict[str, list[dict[str, str]]] = {
    "fresh": [
        {"id": "f1", "label": "清新动画", "url": _style_url("fresh")},
        {"id": "f2", "label": "柔和光线", "url": _style_url("fresh")},
    ],
    "korean": [
        {"id": "k1", "label": "韩系清新", "url": _style_url("korean")},
        {"id": "k2", "label": "韩系街头", "url": _style_url("korean")},
    ],
    "watercolor": [
        {"id": "w1", "label": "水彩暖色", "url": _style_url("watercolor")},
        {"id": "w2", "label": "水彩午后", "url": _style_url("watercolor")},
    ],
}


def resolve_daily_avatar(
    *,
    style: str = "fresh",
    day: str | None = None,
    image_api_url: str | None = None,
    user_id: str = "",
) -> dict[str, str]:
    """返回当日形象元数据。image_api_url 预留外部生图服务。"""
    day = day or date.today().isoformat()
    pool = STYLE_VARIANTS.get(style) or DAILY_VARIANTS
    digest = hashlib.sha256(f"{day}:{style}".encode()).hexdigest()
    idx = int(digest[:8], 16) % len(pool)
    variant = dict(pool[idx])
    variant["date"] = day
    variant["style"] = style
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
