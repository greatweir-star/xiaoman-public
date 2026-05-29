"""L4 社交关系层 — 小满 + 用户社交关系图"""

from __future__ import annotations

import json
import os
from typing import Any


class SocialLayer:
    """L4: 社交关系层"""

    def __init__(self, user_id: str, xiaoman_dir: str, user_dir: str):
        self.user_id = user_id
        self.xm_path = os.path.join(xiaoman_dir, "social_graph.json")
        self.u_path = os.path.join(user_dir, "social_graph.json")
        self._init_files()

    def _init_files(self):
        for path, template in [(self.xm_path, "xiaoman_social_graph.json"), (self.u_path, "user_social_graph.json")]:
            if not os.path.exists(path):
                template_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "templates", template)
                if os.path.exists(template_path):
                    with open(template_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self, path: str) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, path: str, data: dict[str, Any]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ===== 小满社交 =====

    def get_xiaoman(self) -> dict[str, Any]:
        return self._load(self.xm_path)

    def get_xiaoman_visible(self, relation_level: int = 1) -> dict[str, Any]:
        """根据关系等级返回可见的社交信息"""
        data = self._load(self.xm_path)
        visible = {}
        # Lv.1 可见：同桌
        if relation_level >= 1:
            visible["deskmate"] = data.get("deskmate", {})
        # Lv.2 可见：家庭、闺蜜、老师、宠物
        if relation_level >= 2:
            visible["family"] = data.get("family", [])
            visible["besties"] = data.get("besties", [])
            visible["teachers"] = data.get("teachers", [])
            visible["pets"] = data.get("pets", [])
        # Lv.4 可见：暗恋对象
        if relation_level >= 4:
            visible["crush"] = data.get("crush", {})
        return visible

    # ===== 用户社交 =====

    def get_user(self) -> dict[str, Any]:
        return self._load(self.u_path)

    def add_user_family(self, relation: str, detail: str):
        data = self._load(self.u_path)
        data.setdefault("family", [])
        data["family"].append({"relation": relation, "detail": detail})
        self._save(self.u_path, data)

    def add_user_bestie(self, name: str, detail: str):
        data = self._load(self.u_path)
        data.setdefault("besties", [])
        data["besties"].append({"name": name, "detail": detail})
        self._save(self.u_path, data)

    def set_user_crush(self, description: str):
        data = self._load(self.u_path)
        data["crush"] = {"description": description}
        self._save(self.u_path, data)

    def add_user_teacher(self, subject: str, impression: str):
        data = self._load(self.u_path)
        data.setdefault("teachers", [])
        data["teachers"].append({"subject": subject, "impression": impression})
        self._save(self.u_path, data)

    def set_user_deskmate(self, description: str):
        data = self._load(self.u_path)
        data["deskmate"] = {"description": description}
        self._save(self.u_path, data)

    def add_user_group(self, name: str):
        data = self._load(self.u_path)
        data.setdefault("groups", [])
        data["groups"].append(name)
        self._save(self.u_path, data)

    def update_from_message(self, text: str) -> list[dict[str, Any]]:
        """从对话中检测社交信息变化"""
        changes = []
        # 简单关键词检测
        if "同桌" in text:
            changes.append({"layer": "L4", "change": "deskmate_mentioned"})
        if any(w in text for w in ["喜欢", "暗恋", "心动"]):
            changes.append({"layer": "L4", "change": "crush_mentioned"})
        if any(w in text for w in ["我妈", "我爸", "家里"]):
            changes.append({"layer": "L4", "change": "family_mentioned"})
        if "朋友" in text or "闺蜜" in text:
            changes.append({"layer": "L4", "change": "friend_mentioned"})
        return changes
