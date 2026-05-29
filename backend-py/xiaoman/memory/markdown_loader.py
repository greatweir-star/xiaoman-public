"""轻量 Markdown 记忆加载（MVP）"""

from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


def load_global_memory_snippets() -> str:
    """加载 data/global/*.md，按文件名排序拼接"""
    global_dir = Path(DATA_DIR) / "global"
    if not global_dir.is_dir():
        return ""

    parts: list[str] = []
    for path in sorted(global_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8").strip()
            if text:
                parts.append(f"<!-- {path.name} -->\n{text}")
        except OSError:
            continue
    if not parts:
        return ""
    return "【全局记忆】\n" + "\n\n".join(parts) + "\n\n"
