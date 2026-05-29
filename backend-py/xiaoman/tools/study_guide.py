"""Study Guide Tool — PRD 学习技能：苏格拉底式讲题（不给答案）"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from typing import Any

from xiaoman.session import XiaomanSession
from xiaoman.tool_registry import XiaomanTool

# 学科 → 引导问题模板（MVP：规则库，不调用 LLM 直接给答案）
_SUBJECT_HINTS: dict[str, list[str]] = {
    "math": [
        "先别急着算——题目里给了哪些已知条件？",
        "最后要求的是哪个量？能用自己的话复述一遍吗？",
        "有没有学过的公式或定理能套上？",
        "能不能画个图，把关系标出来？",
    ],
    "physics": [
        "这题涉及哪几个物理量？单位分别是什么？",
        "受力/能量/运动，你更想从哪个角度入手？",
        "有没有类似的例题可以对照？",
    ],
    "chemistry": [
        "反应物、生成物分别是什么？配平了吗？",
        "题目问的是质量、摩尔还是浓度？",
        "有没有守恒定律可以用？",
    ],
    "english": [
        "先读题干，关键词是哪几个？",
        "这句话的主语和谓语分别是什么？",
        "四个选项里，哪个和原文意思最接近？",
    ],
    "chinese": [
        "这段的中心句可能在哪一句？",
        "作者想表达什么情感或观点？",
        "有没有修辞手法需要留意？",
    ],
    "default": [
        "你先说说，卡在哪一步了？",
        "题目里最关键的信息是什么？",
        "如果只能问一个问题，你会问什么？",
    ],
}

_SUBJECT_ALIASES: dict[str, str] = {
    "数学": "math",
    "物理": "physics",
    "化学": "chemistry",
    "英语": "english",
    "语文": "chinese",
    "math": "math",
    "physics": "physics",
    "chemistry": "chemistry",
    "english": "english",
    "chinese": "chinese",
}

# 明显在要直接答案的表述 → 拒绝并引导
_ANSWER_SEEKING = re.compile(
    r"(答案|选[A-Da-d]|多少|等于几|帮我算|直接告诉|给我结果|标准答案)",
)


class StudyGuideTool(XiaomanTool):
    """苏格拉底式讲题：只给思路引导，不给最终答案。"""

    _world_getter: Callable[[str], Any] | None = None

    @classmethod
    def bind_world(cls, getter: Callable[[str], Any]) -> None:
        cls._world_getter = getter

    @property
    def name(self) -> str:
        return "study_guide"

    @property
    def description(self) -> str:
        return (
            "苏格拉底式讲题：用户问作业/题目时调用，只给引导问题，不给最终答案。"
            "action=guide 返回下一步思考提示；detect_subject 可选学科。"
        )

    @property
    def parameters(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["guide"],
                    "description": "guide=返回引导问题",
                },
                "subject": {
                    "type": "string",
                    "description": "学科：数学/物理/化学/英语/语文 或 math/physics 等",
                },
                "question": {
                    "type": "string",
                    "description": "用户描述的题目或卡点",
                },
                "step": {
                    "type": "integer",
                    "description": "引导轮次 0–3，默认 0",
                },
            },
            "required": ["action"],
        }

    def __call__(self, session: XiaomanSession, arguments: Mapping[str, Any]) -> str:
        action = str(arguments.get("action") or "guide").strip()
        if action != "guide":
            return json.dumps({"ok": False, "message": "未知 action"}, ensure_ascii=False)

        question = str(arguments.get("question") or "").strip()
        subject_raw = str(arguments.get("subject") or "").strip().lower()
        step = max(0, min(3, int(arguments.get("step") or 0)))

        if _ANSWER_SEEKING.search(question):
            return json.dumps(
                {
                    "ok": True,
                    "mode": "refuse_answer",
                    "hints": [
                        "我不能直接给答案哦，但我们可以一起想～",
                        "你先说说自己做到哪一步了？",
                    ],
                    "message": "拒绝直接给答案，引导用户自述进度",
                },
                ensure_ascii=False,
            )

        subject_key = _detect_subject(subject_raw, question)
        hints = _SUBJECT_HINTS.get(subject_key, _SUBJECT_HINTS["default"])
        hint = hints[step % len(hints)]

        return json.dumps(
            {
                "ok": True,
                "mode": "socratic",
                "subject": subject_key,
                "hint": hint,
                "step": step,
                "next_step": step + 1,
                "message": f"引导问题：{hint}",
                "policy": "不给最终答案，只引导思考",
            },
            ensure_ascii=False,
        )


def _detect_subject(subject_raw: str, question: str) -> str:
    if subject_raw in _SUBJECT_ALIASES:
        return _SUBJECT_ALIASES[subject_raw]
    for alias, key in _SUBJECT_ALIASES.items():
        if alias in subject_raw or alias in question:
            return key
    if any(w in question for w in ("方程", "函数", "几何", "证明", "计算")):
        return "math"
    if any(w in question for w in ("力", "速度", "电路", "牛顿")):
        return "physics"
    return "default"
