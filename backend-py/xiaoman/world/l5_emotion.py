"""L5 情绪心理层 — 小满 + 用户情绪心理"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime
from typing import Any


class EmotionLayer:
    """L5: 情绪心理层"""

    EMOTIONS = ["开心", "累", "烦", "焦虑", "无聊", "温柔", "平静"]

    def __init__(self, user_id: str, xiaoman_dir: str, user_dir: str):
        self.user_id = user_id
        self.xm_path = os.path.join(xiaoman_dir, "emotions.json")
        self.u_path = os.path.join(user_dir, "emotions.json")
        self._init_files()

    def _init_files(self):
        for path, template in [(self.xm_path, "xiaoman_emotions.json"), (self.u_path, "user_emotions.json")]:
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

    # ===== 小满情绪 =====

    def get_xiaoman(self) -> dict[str, Any]:
        return self._load(self.xm_path)

    def set_xiaoman_emotion(self, emotion: str, reason: str = ""):
        data = self._load(self.xm_path)
        data["current_emotion"] = emotion
        data["updated_at"] = datetime.now().isoformat()
        self._save(self.xm_path, data)

    def update_xiaoman_energy(self, delta: int):
        data = self._load(self.xm_path)
        data["energy"] = max(0, min(100, data.get("energy", 50) + delta))
        self._save(self.xm_path, data)

    def update_xiaoman_security(self, delta: int):
        data = self._load(self.xm_path)
        data["security"] = max(0, min(100, data.get("security", 50) + delta))
        self._save(self.xm_path, data)

    def update_xiaoman_loneliness(self, delta: int):
        data = self._load(self.xm_path)
        data["loneliness"] = max(0, min(100, data.get("loneliness", 30) + delta))
        self._save(self.xm_path, data)

    def apply_turn_energy_decay(self, *, period: str = "normal", in_class: bool = False) -> dict[str, Any]:
        """每轮对话后精力自然衰减，写回 emotions.json。"""
        decay_map = {
            "morning": 2,
            "lunch": 1,
            "class": 3 if in_class else 2,
            "after_class": 2,
            "homework": 3,
            "sleep": 1,
        }
        delta = -decay_map.get(period, 2)
        data = self._load(self.xm_path)
        before = int(data.get("energy", 50))
        after = max(0, min(100, before + delta))
        data["energy"] = after
        data["updated_at"] = datetime.now().isoformat()
        self._save(self.xm_path, data)
        return {
            "layer": "L5",
            "change": "energy_decay",
            "delta": delta,
            "energy": after,
        }

    def apply_auth_energy_decay(self) -> dict[str, Any]:
        """重连/auth 时轻微精力衰减（-1）。"""
        return self.apply_tick_energy_decay(-1, change="auth_energy_decay")

    def apply_tick_energy_decay(self, delta: int, *, change: str = "energy_tick") -> dict[str, Any]:
        data = self._load(self.xm_path)
        before = int(data.get("energy", 50))
        after = max(0, min(100, before + delta))
        data["energy"] = after
        data["updated_at"] = datetime.now().isoformat()
        self._save(self.xm_path, data)
        return {"layer": "L5", "change": change, "delta": delta, "energy": after}

    def update_xiaoman_from_user(self, user_text: str) -> list[dict[str, Any]]:
        """根据用户输入联动更新小满情绪"""
        changes = []
        data = self._load(self.xm_path)

        # 用户说开心 → 小满也开心
        if any(w in user_text for w in ["开心", "高兴", "棒", "耶"]):
            data["current_emotion"] = "开心"
            data["energy"] = min(100, data.get("energy", 50) + 10)
            changes.append({"layer": "L5", "change": "xiaoman_mirror_joy", "emotion": "开心"})

        # 用户说累 → 小满也累
        elif any(w in user_text for w in ["累", "困", "疲惫"]):
            data["current_emotion"] = "累"
            data["energy"] = max(0, data.get("energy", 50) - 10)
            changes.append({"layer": "L5", "change": "xiaoman_mirror_tired", "emotion": "累"})

        # 用户说烦 → 小满也烦
        elif any(w in user_text for w in ["烦", "讨厌", "郁闷"]):
            data["current_emotion"] = "烦"
            changes.append({"layer": "L5", "change": "xiaoman_mirror_annoyed", "emotion": "烦"})

        # 深夜 → 孤独感上升
        hour = datetime.now().hour
        if hour >= 23 or hour < 6:
            data["loneliness"] = min(100, data.get("loneliness", 30) + 5)
            changes.append({"layer": "L5", "change": "night_loneliness_up"})

        self._save(self.xm_path, data)
        return changes

    # ===== 用户情绪 =====

    def get_user(self) -> dict[str, Any]:
        return self._load(self.u_path)

    def detect_user_emotion(self, text: str) -> list[dict[str, Any]]:
        """检测用户情绪"""
        changes = []
        emotion_map = {
            "累": ["累", "困", "好累"],
            "开心": ["开心", "高兴", "棒", "耶", "哈哈"],
            "烦": ["烦", "好烦", "讨厌", "郁闷"],
            "难过": ["难过", "伤心", "哭", "失望"],
            "焦虑": ["焦虑", "紧张", "怕", "担心", "压力"],
            "无聊": ["无聊", "没意思", "没劲"],
        }

        detected = "平静"
        for emotion, keywords in emotion_map.items():
            if any(kw in text for kw in keywords):
                detected = emotion
                break

        data = self._load(self.u_path)
        data["current_emotion"] = detected

        # 压力检测
        if "压力" in text or "焦虑" in text:
            data["stress_level"] = min(100, data.get("stress_level", 0) + 10)
            changes.append({"layer": "L5", "change": "user_stress_up", "level": data["stress_level"]})

        # 开心来源
        if detected == "开心":
            # 尝试提取开心原因
            data.setdefault("joy_sources", [])
            changes.append({"layer": "L5", "change": "user_joy_detected"})

        self._save(self.u_path, data)
        return changes

    def add_joy_source(self, source: str):
        data = self._load(self.u_path)
        data.setdefault("joy_sources", [])
        if source not in data["joy_sources"]:
            data["joy_sources"].append(source)
        self._save(self.u_path, data)

    def add_worry_source(self, source: str):
        data = self._load(self.u_path)
        data.setdefault("worry_sources", [])
        if source not in data["worry_sources"]:
            data["worry_sources"].append(source)
        self._save(self.u_path, data)
