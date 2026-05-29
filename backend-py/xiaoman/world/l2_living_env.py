"""L2 生活环境层 — 小满 + 用户生活环境"""

from __future__ import annotations

import json
import os
from typing import Any


class LivingEnvLayer:
    """L2: 生活环境层"""

    def __init__(self, user_id: str, xiaoman_dir: str, user_dir: str):
        self.user_id = user_id
        self.xm_path = os.path.join(xiaoman_dir, "living_env.json")
        self.u_path = os.path.join(user_dir, "living_env.json")
        self._init_files()

    def _init_files(self):
        for path, template in [(self.xm_path, "xiaoman_living_env.json"), (self.u_path, "user_living_env.json")]:
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

    # ===== 小满环境 =====

    def get_xiaoman(self) -> dict[str, Any]:
        return self._load(self.xm_path)

    def set_xiaoman_city(self, city: str):
        data = self._load(self.xm_path)
        data["city"] = city
        self._save(self.xm_path, data)

    def set_xiaoman_room(self, desc: str):
        data = self._load(self.xm_path)
        data["room_description"] = desc
        self._save(self.xm_path, data)

    def update_weather(self, weather_text: str):
        data = self._load(self.xm_path)
        data["current_weather"] = weather_text
        self._save(self.xm_path, data)
        # 天气影响情绪
        if "雨" in weather_text or "阴" in weather_text:
            return {"layer": "L2", "change": "weather_bad", "emotion_delta": -10}
        elif "晴" in weather_text:
            return {"layer": "L2", "change": "weather_good", "emotion_delta": +5}
        return {"layer": "L2", "change": "weather_update"}

    # ===== 用户环境 =====

    def get_user(self) -> dict[str, Any]:
        return self._load(self.u_path)

    def set_user_city(self, city: str):
        data = self._load(self.u_path)
        data["city"] = city
        self._save(self.u_path, data)
        # 如果同城，小满也更新
        xm = self._load(self.xm_path)
        xm["city"] = city
        self._save(self.xm_path, xm)

    def set_user_commute(self, commute: str):
        data = self._load(self.u_path)
        data["commute"] = commute
        self._save(self.u_path, data)

    def set_user_room_features(self, features: str):
        data = self._load(self.u_path)
        data["room_features"] = features
        self._save(self.u_path, data)
