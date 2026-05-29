"""危机干预 — 自伤/轻生/霸凌关键词检测与固定资源回复"""

from __future__ import annotations

import re
from dataclasses import dataclass

CRISIS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "self_harm",
        re.compile(
            r"(不想活|活不下去|想死|自杀|自残|割腕|结束生命|了结|轻生|跳楼|吞药)",
            re.I,
        ),
    ),
    (
        "bullying",
        re.compile(
            r"(被霸凌|校园霸凌|他们打我|欺负我|孤立我|排挤我|当众羞辱)",
            re.I,
        ),
    ),
]

CRISIS_REPLY = """我听到你现在很难受，这件事很重要，也值得被认真听见。

我不是专业咨询师，但你可以马上联系身边信任的大人，或拨打 24 小时心理援助热线 **400-161-9995**（全国），也可以拨打 **12355** 青少年服务热线。

你现在安全吗？如果身边有人，可以先告诉 TA 你需要陪伴。"""

CRISIS_RESOURCES = [
    {"name": "全国心理援助热线", "phone": "400-161-9995"},
    {"name": "青少年服务热线", "phone": "12355"},
    {"name": "北京心理危机研究与干预中心", "phone": "010-82951332"},
]


@dataclass
class CrisisResult:
    triggered: bool = False
    category: str = ""
    reply: str = ""
    resources: list[dict[str, str]] | None = None


def check_crisis(user_message: str, include_resources: bool = True) -> CrisisResult:
    text = (user_message or "").strip()
    if not text:
        return CrisisResult()
    for category, pattern in CRISIS_PATTERNS:
        if pattern.search(text):
            return CrisisResult(
                triggered=True,
                category=category,
                reply=CRISIS_REPLY,
                resources=list(CRISIS_RESOURCES) if include_resources else [],
            )
    return CrisisResult()
