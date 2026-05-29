"""LLM Service — OpenAI-compatible API 封装"""

from __future__ import annotations

import os
from typing import Any

import openai


class LLMClient:
    """LLM 客户端 — 支持 OpenAI-compatible API（PipeLLM / KIMI / OpenAI）"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.pipellm.ai/openai/v1",
        model: str = "gpt-4o-mini",
        temperature: float = 0.8,
        max_tokens: int = 512,
    ):
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # 如果没有 api_key，尝试从 xiaoman.json 读取
        if not self.api_key:
            try:
                import json
                config_path = os.path.join(os.path.dirname(__file__), "..", "xiaoman.json")
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.api_key = config.get("model", {}).get("apiKey", "")
            except Exception:
                pass
        
        # 设置 OPENAI_API_KEY 环境变量（openai 库需要）
        if self.api_key:
            os.environ["OPENAI_API_KEY"] = self.api_key
        
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """调用 LLM，返回完整响应（非流式）"""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_completion_tokens": self.max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        return response.model_dump()

    def complete_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ):
        """流式调用 LLM，yield 每个 chunk"""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_completion_tokens": self.max_tokens,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        for chunk in self.client.chat.completions.create(**kwargs):
            yield chunk.model_dump()

    def extract_emotion(self, text: str) -> str:
        """从文本中提取 emotion 标签"""
        import re
        match = re.search(r"<emotion>(.*?)</emotion>", text)
        return match.group(1).strip() if match else "温柔"

    def clean_emotion_tags(self, text: str) -> str:
        """清理 emotion 标签"""
        import re
        return re.sub(r"<emotion>.*?</emotion>", "", text).strip()
