"""Tool Registry — 参考 OpenRath flow/tool/tool_table.py + base.py 设计"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from xiaoman.session import XiaomanSession


class XiaomanTool(ABC):
    """Tool 统一抽象 — 参考 OpenRath FlowToolCall
    
    每个 tool 必须实现：
    - name: 工具名
    - description: 描述（给 LLM 看的）
    - parameters: JSON Schema（给 LLM 看的参数定义）
    - __call__: 执行逻辑
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def description(self) -> str | None:
        return None

    @property
    @abstractmethod
    def parameters(self) -> Mapping[str, Any]: ...

    @abstractmethod
    def __call__(self, session: XiaomanSession, arguments: Mapping[str, Any]) -> Any:
        """Execute the tool"""


def merge_tools(user_tools: list[XiaomanTool] | None) -> dict[str, XiaomanTool]:
    """合并用户工具和系统工具 — 参考 OpenRath merge_tools_for_loop"""
    table: dict[str, XiaomanTool] = {}
    for t in user_tools or ():
        table[t.name] = t
    return table


def tools_to_schemas(tools: Mapping[str, XiaomanTool]) -> list[dict[str, Any]]:
    """转换为 OpenAI function calling 格式"""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": dict(tool.parameters),
            },
        }
        for _, tool in sorted(tools.items(), key=lambda kv: kv[0])
    ]
