"""Memory Update Tool — 更新用户记忆（用户级存储）"""

from datetime import datetime
from typing import Any

from xiaoman.tool_registry import XiaomanTool


class MemoryUpdateTool(XiaomanTool):
    """更新用户的关键信息到记忆系统"""

    name = "memory_update"
    description = "更新用户的关键信息（名字、年级、喜好等）到记忆中"

    parameters = {
        "type": "object",
        "properties": {
            "fact": {
                "type": "string",
                "description": "要保存的事实，例如：用户叫小明、用户初三",
            },
            "category": {
                "type": "string",
                "description": "事实分类：identity/preference/event/emotion/relation",
                "enum": ["identity", "preference", "event", "emotion", "relation", "interest"],
            },
            "layer": {
                "type": "string",
                "description": "记忆层 L1-L8",
            },
        },
        "required": ["fact"],
    }

    _memory_engine: Any = None

    @classmethod
    def bind_engine(cls, engine: Any) -> None:
        cls._memory_engine = engine

    def execute(self, fact: str, category: str = "event", layer: str = "L7") -> str:
        from xiaoman.memory.user_name import extract_name_from_text

        if extract_name_from_text(fact):
            category = "identity"
            layer = "L1"
        user_id = getattr(self, "_user_id", None) or getattr(self, "_session_id", "unknown")
        if self._memory_engine:
            saved = self._memory_engine.save_fact(user_id, fact, category, layer)
            getter = getattr(self._memory_engine.extractor, "_world_getter", None)
            if saved and getter and (world := getter(user_id)):
                from xiaoman.world.fact_router import apply_facts_to_world

                apply_facts_to_world(
                    world,
                    [{"content": fact, "category": category, "layer": layer}],
                )
            return f"已保存记忆：{fact}"
        return f"已记录（引擎未绑定）：{fact}"

    def __call__(self, session, arguments):
        self._user_id = session.user_id or session.id
        return self.execute(
            fact=arguments.get("fact", ""),
            category=arguments.get("category", "event"),
            layer=arguments.get("layer", "L7"),
        )
