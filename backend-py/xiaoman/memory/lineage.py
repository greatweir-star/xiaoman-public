"""Lineage Tracker — 血缘追踪（记忆因果链）

参考 OpenRath session/graph/recording.py 设计。

核心概念：
- 每个记忆有唯一 ID
- 记忆之间有父子关系（提取来源、整理生成）
- 血缘图记录记忆的演变历史
- 支持溯源：一个记忆是怎么来的？

用途：
1. 溯源：小满提到某个记忆时，可以追溯到原始对话
2. 因果链：A记忆导致B记忆产生
3. 版本管理：记忆被更新时保留历史版本
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

from xiaoman.paths import DATA_DIR


class MemoryNode:
    """记忆节点 — 血缘图中的一个节点"""

    def __init__(
        self,
        node_id: str,
        content: str,
        node_type: str,  # "extract" | "organize" | "dream" | "promote"
        parent_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.node_id = node_id
        self.content = content
        self.node_type = node_type
        self.parent_ids = parent_ids or []
        self.children_ids: list[str] = []
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "content": self.content,
            "node_type": self.node_type,
            "parent_ids": self.parent_ids,
            "children_ids": self.children_ids,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryNode:
        node = cls(
            node_id=data["node_id"],
            content=data["content"],
            node_type=data["node_type"],
            parent_ids=data.get("parent_ids", []),
            metadata=data.get("metadata", {}),
        )
        node.children_ids = data.get("children_ids", [])
        node.created_at = data.get("created_at", datetime.now().isoformat())
        return node


class LineageTracker:
    """血缘追踪器 — 管理记忆的血缘图（按 user_id 持久化）"""

    def __init__(self, owner_id: str, data_dir: str = DATA_DIR):
        self.owner_id = owner_id
        self.data_dir = data_dir
        self.nodes: dict[str, MemoryNode] = {}
        self._load()

    def _lineage_path(self) -> str:
        safe = self.owner_id.replace("/", "_")
        return os.path.join(self.data_dir, "users", safe, "memory", "lineage.json")

    def _load(self) -> None:
        """加载血缘图"""
        path = self._lineage_path()
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for node_data in data.get("nodes", []):
                node = MemoryNode.from_dict(node_data)
                self.nodes[node.node_id] = node

    def _save(self) -> None:
        """保存血缘图"""
        path = self._lineage_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "owner_id": self.owner_id,
            "updated_at": datetime.now().isoformat(),
            "nodes": [node.to_dict() for node in self.nodes.values()],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_node(
        self,
        content: str,
        node_type: str,
        parent_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """添加节点，返回 node_id"""
        node_id = str(uuid.uuid4())
        node = MemoryNode(
            node_id=node_id,
            content=content,
            node_type=node_type,
            parent_ids=parent_ids or [],
            metadata=metadata,
        )
        self.nodes[node_id] = node
        
        # 更新父节点的 children_ids
        for parent_id in node.parent_ids:
            if parent_id in self.nodes:
                self.nodes[parent_id].children_ids.append(node_id)
        
        self._save()
        logger.info("Lineage node added: %s (type=%s)", node_id, node_type)
        return node_id

    def trace(self, node_id: str) -> list[MemoryNode]:
        """溯源：从节点追溯到根节点"""
        path: list[MemoryNode] = []
        current_id = node_id
        visited: set[str] = set()
        
        while current_id and current_id in self.nodes and current_id not in visited:
            visited.add(current_id)
            node = self.nodes[current_id]
            path.append(node)
            # 取第一个父节点继续追溯
            current_id = node.parent_ids[0] if node.parent_ids else None
        
        return list(reversed(path))

    def trace_all_parents(self, node_id: str) -> list[list[MemoryNode]]:
        """追溯所有父节点路径（支持多父节点）"""
        if node_id not in self.nodes:
            return []
        
        node = self.nodes[node_id]
        if not node.parent_ids:
            return [[node]]
        
        all_paths: list[list[MemoryNode]] = []
        for parent_id in node.parent_ids:
            parent_paths = self.trace_all_parents(parent_id)
            for path in parent_paths:
                all_paths.append(path + [node])
        
        return all_paths

    def get_descendants(self, node_id: str) -> list[MemoryNode]:
        """获取所有后代节点"""
        if node_id not in self.nodes:
            return []
        
        descendants: list[MemoryNode] = []
        queue = [node_id]
        visited: set[str] = set()
        
        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)
            
            if current_id != node_id and current_id in self.nodes:
                descendants.append(self.nodes[current_id])
            
            if current_id in self.nodes:
                queue.extend(self.nodes[current_id].children_ids)
        
        return descendants

    def get_impact_graph(self, node_id: str) -> dict[str, Any]:
        """获取影响图：这个记忆影响了哪些其他记忆"""
        descendants = self.get_descendants(node_id)
        return {
            "source_node": self.nodes.get(node_id, None),
            "affected_nodes": [n.to_dict() for n in descendants],
            "total_impact": len(descendants),
        }

    def get_children(self, node_id: str) -> list[MemoryNode]:
        """获取节点的所有子节点"""
        if node_id not in self.nodes:
            return []
        return [self.nodes[cid] for cid in self.nodes[node_id].children_ids if cid in self.nodes]

    def get_lineage_summary(self, node_id: str) -> str:
        """生成血缘摘要"""
        trace = self.trace(node_id)
        if not trace:
            return "未知来源"
        
        steps = []
        for i, node in enumerate(trace):
            type_names = {
                "extract": "从对话中提取",
                "organize": "整理生成",
                "dream": "梦境生成",
                "promote": "记忆提升",
            }
            type_name = type_names.get(node.node_type, node.node_type)
            steps.append(f"{i+1}. {type_name}: {node.content[:30]}...")
        
        return " → ".join(steps)
