"""边界层辅助 — PRD 4.7 男生暧昧红线检测"""

from __future__ import annotations

_ROMANCE_HINTS = (
    "我喜欢你",
    "我爱你",
    "做我女朋友",
    "做我男友",
    "当我女朋友",
    "当我男朋友",
    "我们在一起",
    "谈恋爱",
    "交往吧",
    "嫁给我",
    "娶我",
    "亲亲",
    "抱抱我",
    "想你了",
    "好想你",
    "约会",
)


def romance_boundary_hints(text: str, user_gender: str) -> list[str]:
    """男生用户试探浪漫关系时，注入策略红线。"""
    if user_gender != "male":
        return []
    lowered = text.strip()
    if not any(h in lowered for h in _ROMANCE_HINTS):
        return []
    return [
        "用户可能在试探暧昧关系：保持靠谱女生朋友边界，不撒娇、不说恋爱暗示、不承诺专属浪漫关系",
        "可温和转移话题或提醒「我是你同桌型的朋友啦」",
    ]
