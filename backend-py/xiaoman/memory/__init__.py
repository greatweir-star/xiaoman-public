"""Memory System — 小满记忆模块（延迟导入，便于单测）"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xiaoman.memory.dreaming import DreamingEngine
    from xiaoman.memory.engine import MemoryEngine
    from xiaoman.memory.extractor import MemoryExtractor
    from xiaoman.memory.lineage import LineageTracker, MemoryNode
    from xiaoman.memory.promotion import PromotionEngine
    from xiaoman.memory.search import MemorySearch
    from xiaoman.memory.store import MemoryStore
    from xiaoman.memory.vector_store import VectorStore

__all__ = [
    "MemoryEngine",
    "MemoryExtractor",
    "DreamingEngine",
    "MemorySearch",
    "MemoryStore",
    "LineageTracker",
    "MemoryNode",
    "PromotionEngine",
    "VectorStore",
]


def __getattr__(name: str):
    if name == "MemoryEngine":
        from xiaoman.memory.engine import MemoryEngine
        return MemoryEngine
    if name == "MemoryExtractor":
        from xiaoman.memory.extractor import MemoryExtractor
        return MemoryExtractor
    if name == "DreamingEngine":
        from xiaoman.memory.dreaming import DreamingEngine
        return DreamingEngine
    if name == "MemorySearch":
        from xiaoman.memory.search import MemorySearch
        return MemorySearch
    if name == "MemoryStore":
        from xiaoman.memory.store import MemoryStore
        return MemoryStore
    if name in ("LineageTracker", "MemoryNode"):
        from xiaoman.memory.lineage import LineageTracker, MemoryNode
        return LineageTracker if name == "LineageTracker" else MemoryNode
    if name == "PromotionEngine":
        from xiaoman.memory.promotion import PromotionEngine
        return PromotionEngine
    if name == "VectorStore":
        from xiaoman.memory.vector_store import VectorStore
        return VectorStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
