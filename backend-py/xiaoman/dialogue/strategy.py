"""Phase 3 推理决策 — 策略提示注入 Prompt"""

from __future__ import annotations

from xiaoman.dialogue.input_parser import ParsedInput
from xiaoman.dialogue.period import PeriodInfo


_STRATEGY = {
    "vent": "情绪优先：先承接吐槽，别急着给建议",
    "share": "共情优先：接话并分享一点自己的小日常",
    "seek_help": "先陪想，苏格拉底式引导，不直接给答案",
    "keep_company": "自然接话，像同桌闲聊",
    "small_talk": "轻松随意，1-3 句话",
    "greeting": "简短回应，可带时间场景",
}


def build_strategy_prompt(
    parsed: ParsedInput,
    period: PeriodInfo,
    user_gender: str,
    *,
    last_topic: str = "",
    consecutive_low_mood: int = 0,
    extra_hints: list[str] | None = None,
) -> str:
    tone = "闺蜜模式，互怼式关心" if user_gender != "male" else "靠谱女生朋友，友好有边界"
    if parsed.emotion in ("难过", "烦躁", "焦虑", "疲惫"):
        tone = "先接住情绪再问细节" if user_gender != "male" else "温和理性，先认可感受"

    lines = [
        "【对话策略】",
        f"消息类型：{parsed.message_type}",
        f"用户意图：{parsed.intent} → {_STRATEGY.get(parsed.intent, _STRATEGY['small_talk'])}",
        f"用户情绪：{parsed.emotion}",
        f"语气：{tone}",
        f"小满此刻：{period.period}（{period.reply_style}）",
    ]
    if parsed.keywords:
        lines.append(f"关键词：{', '.join(parsed.keywords[:6])}")
    if last_topic:
        lines.append(f"刚才在聊：{last_topic}")
    if consecutive_low_mood >= 3:
        lines.append("用户连续几轮情绪低落，可主动提议聊点别的转移心情")
    if period.in_class:
        lines.append("上课中，回复要短，可以偷偷回")
    lines.append("回复控制在 2-3 句话")
    for hint in extra_hints or []:
        lines.append(f"- {hint}")
    return "\n".join(lines)
