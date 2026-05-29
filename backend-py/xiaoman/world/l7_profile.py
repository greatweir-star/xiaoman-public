"""L7 用户画像层 — 小满对用户的理解 + 用户对小满的理解"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from typing import Any

from xiaoman.security.secret_vault import SecretVault


class ProfileLayer:
    """L7: 用户画像层（双向）"""

    def __init__(self, user_id: str, xiaoman_dir: str, user_dir: str):
        self.user_id = user_id
        self._vault = SecretVault()
        self.xm_dir = xiaoman_dir
        self.u_dir = user_dir
        self.u_path = os.path.join(user_dir, "profile.json")
        self.xm_understanding_path = os.path.join(xiaoman_dir, "user_understanding.json")
        self._init_files()

    def _init_files(self):
        for path, template in [
            (self.u_path, "user_profile.json"),
        ]:
            if not os.path.exists(path):
                template_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "templates", template)
                if os.path.exists(template_path):
                    with open(template_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

        if not os.path.exists(self.xm_understanding_path):
            default = {
                "name": "",
                "personality_impression": "",
                "likes": [],
                "dislikes": [],
                "secrets": [],
                "emotion_patterns": [],
                "emotional_weather": {
                    "last_mood": "还没聊过",
                    "trigger": "",
                    "since": "",
                    "pattern_note": "",
                },
                "growth_trajectory": [],
                "exclusive_memories": [],
            }
            os.makedirs(os.path.dirname(self.xm_understanding_path), exist_ok=True)
            with open(self.xm_understanding_path, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)

    def _load(self, path: str) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, path: str, data: dict[str, Any]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ===== 小满对用户的理解 =====

    def get_xiaoman_understanding(self) -> dict[str, Any]:
        return self._load(self.xm_understanding_path)

    def set_xiaoman_name_for_user(self, name: str):
        data = self._load(self.xm_understanding_path)
        data["name"] = name
        self._save(self.xm_understanding_path, data)

    def set_personality_impression(self, impression: str):
        data = self._load(self.xm_understanding_path)
        data["personality_impression"] = impression
        self._save(self.xm_understanding_path, data)

    def add_like(self, item: str):
        data = self._load(self.xm_understanding_path)
        data.setdefault("likes", [])
        if item not in data["likes"]:
            data["likes"].append(item)
        self._save(self.xm_understanding_path, data)

    def add_dislike(self, item: str):
        data = self._load(self.xm_understanding_path)
        data.setdefault("dislikes", [])
        if item not in data["dislikes"]:
            data["dislikes"].append(item)
        self._save(self.xm_understanding_path, data)

    def add_secret(self, secret: str, level: str = "medium", sensitivity: int = 3):
        data = self._load(self.xm_understanding_path)
        data.setdefault("secrets", [])
        data["secrets"].append({
            "id": str(uuid.uuid4())[:8],
            "content_encrypted": self._vault.encrypt(secret, self.user_id),
            "level": level,
            "sensitivity": sensitivity,
            "timestamp": datetime.now().isoformat(),
        })
        self._save(self.xm_understanding_path, data)

    def list_secrets(self, reveal: bool = False) -> list[dict[str, Any]]:
        data = self._load(self.xm_understanding_path)
        secrets = data.get("secrets", [])
        return [self._vault.redact_for_display(s, self.user_id, reveal=reveal) for s in secrets]

    def add_emotion_pattern(self, pattern: str):
        data = self._load(self.xm_understanding_path)
        data.setdefault("emotion_patterns", [])
        if pattern not in data["emotion_patterns"]:
            data["emotion_patterns"].append(pattern)
        self._save(self.xm_understanding_path, data)

    def get_emotional_weather(self) -> dict[str, Any]:
        data = self._load(self.xm_understanding_path)
        return dict(data.get("emotional_weather") or {})

    def update_emotional_weather_heuristic(
        self, user_text: str, detected_emotion: str
    ) -> dict[str, Any]:
        data = self._load(self.xm_understanding_path)
        weather = dict(data.get("emotional_weather") or {})
        now = datetime.now().isoformat()
        weather["last_mood"] = detected_emotion or weather.get("last_mood", "平静")
        weather["since"] = now
        for kw in ("因为", "由于", "烦", "考", "妈", "爸", "同学", "老师"):
            if kw in user_text:
                weather["trigger"] = user_text.strip()[:80]
                break
        data["emotional_weather"] = weather
        self._save(self.xm_understanding_path, data)
        return weather

    def merge_emotional_weather_llm(self, patch: dict[str, Any]) -> None:
        data = self._load(self.xm_understanding_path)
        weather = dict(data.get("emotional_weather") or {})
        for key in ("last_mood", "trigger", "pattern_note"):
            val = patch.get(key)
            if val:
                weather[key] = str(val)[:200]
        note = weather.get("pattern_note")
        if note:
            patterns = data.setdefault("emotion_patterns", [])
            if note not in patterns:
                patterns.append(note)
        weather["since"] = datetime.now().isoformat()
        data["emotional_weather"] = weather
        self._save(self.xm_understanding_path, data)

    def list_growth_moments(self, limit: int = 50) -> list[dict[str, Any]]:
        data = self._load(self.xm_understanding_path)
        items = list(data.get("growth_trajectory") or [])
        return items[-limit:]

    def add_growth_moment(self, summary: str, *, source: str = "chat") -> bool:
        text = (summary or "").strip()
        if not text:
            return False
        data = self._load(self.xm_understanding_path)
        moments = data.setdefault("growth_trajectory", [])
        if any(m.get("summary") == text for m in moments if isinstance(m, dict)):
            return False
        moments.append({
            "id": str(uuid.uuid4())[:8],
            "summary": text,
            "source": source,
            "timestamp": datetime.now().isoformat(),
        })
        if len(moments) > 100:
            data["growth_trajectory"] = moments[-100:]
        self._save(self.xm_understanding_path, data)
        return True

    def add_exclusive_memory(self, memory: str):
        data = self._load(self.xm_understanding_path)
        data.setdefault("exclusive_memories", [])
        data["exclusive_memories"].append({
            "content": memory,
            "timestamp": datetime.now().isoformat(),
        })
        self._save(self.xm_understanding_path, data)

    # ===== 用户画像（用户对自己的记录） =====

    def get_user(self) -> dict[str, Any]:
        return self._load(self.u_path)

    def update_from_message(self, text: str) -> list[dict[str, Any]]:
        """从对话中提取画像信息"""
        changes = []

        # 提取喜好
        like_patterns = [
            r"我喜欢(.+?)[，。！]",
            r"最爱(.+?)[，。！]",
            r"喜欢(.+?)[，。！]",
        ]
        for pattern in like_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                self.add_like(match.strip())
                changes.append({"layer": "L7", "change": "like_added", "item": match.strip()})

        # 提取厌恶
        dislike_patterns = [
            r"我讨厌(.+?)[，。！]",
            r"不喜欢(.+?)[，。！]",
            r"烦(.+?)[，。！]",
        ]
        for pattern in dislike_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                self.add_dislike(match.strip())
                changes.append({"layer": "L7", "change": "dislike_added", "item": match.strip()})

        # 提取秘密
        if any(w in text for w in ["其实", "秘密", "没告诉别人", "只告诉你"]):
            changes.append({"layer": "L7", "change": "secret_mentioned"})

        return changes
