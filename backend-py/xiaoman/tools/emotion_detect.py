"""Emotion Detect Tool — 检测用户情感"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from xiaoman.session import XiaomanSession
from xiaoman.tool_registry import XiaomanTool


class EmotionDetectTool(XiaomanTool):
    """检测用户情感 — LLM 可调用，也可后端硬编码 fallback"""

    @property
    def name(self) -> str:
        return "emotion_detect"

    @property
    def description(self) -> str:
        return "检测用户当前情感状态。传入用户消息文本，返回主要情绪。"

    @property
    def parameters(self) -> Mapping[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "用户消息文本",
                },
            },
            "required": ["text"],
        }

    def __call__(self, session: XiaomanSession, arguments: Mapping[str, Any]) -> str:
        text = arguments.get("text", "")
        
        # 关键词规则（MVP 阶段先用规则，V0.2 引入 LLM 辅助）
        emotions = {
            "累": ["累", "困", "好累", " exhaustion"],
            "开心": ["开心", "高兴", "棒", "耶", "哈哈"],
            "烦": ["烦", "好烦", "讨厌", "郁闷"],
            "难过": ["难过", "伤心", "哭", "失望"],
            "焦虑": ["焦虑", "紧张", "怕", "担心"],
            "无聊": ["无聊", "没意思", "没劲"],
        }
        
        for emotion, keywords in emotions.items():
            if any(kw in text for kw in keywords):
                session.emotion_state = emotion
                return json.dumps({"emotion": emotion, "confidence": 0.8})
        
        return json.dumps({"emotion": "平静", "confidence": 0.5})


import json
