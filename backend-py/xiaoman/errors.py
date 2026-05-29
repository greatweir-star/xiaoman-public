"""Error Handling — 参考 OpenRath 错误处理设计"""

from __future__ import annotations


class XiaomanError(Exception):
    """基础错误"""
    pass


class BudgetExceededError(XiaomanError):
    """Token 预算超出"""
    def __init__(self, total: int, cap: int):
        self.total = total
        self.cap = cap
        super().__init__(f"Budget exceeded: {total} > {cap}")


class ToolExecutionError(XiaomanError):
    """Tool 执行失败"""
    def __init__(self, tool_name: str, message: str, detail: str | None = None):
        self.tool_name = tool_name
        self.detail = detail
        super().__init__(f"Tool '{tool_name}' failed: {message}")


class ToolNotFoundError(XiaomanError):
    """Tool 未找到"""
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}' not found")


class LLMError(XiaomanError):
    """LLM 调用失败"""
    pass


def format_tool_error(kind: str, message: str, detail: str | None = None) -> dict[str, Any]:
    """格式化 tool 错误为 JSON payload"""
    from typing import Any
    payload: dict[str, Any] = {"kind": kind, "message": message}
    if detail:
        payload["detail"] = detail
    return payload
