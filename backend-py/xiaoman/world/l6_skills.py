"""L6 知识技能层 — 小满技能树 + 用户学习"""

from __future__ import annotations

import json
import os
from typing import Any


class SkillsLayer:
    """L6: 知识技能层"""

    SKILL_TREE = {
        "新同桌": {
            "level": 1,
            "skills": [
                {"name": "主动打招呼", "max_level": 1, "unlock_at": 0},
                {"name": "情绪承接", "max_level": 5, "unlock_at": 0},
            ],
        },
        "饭搭子": {
            "level": 2,
            "skills": [
                {"name": "讲笑话", "max_level": 3, "unlock_at": 20},
                {"name": "分享日常", "max_level": 3, "unlock_at": 20},
            ],
        },
        "树洞": {
            "level": 3,
            "skills": [
                {"name": "深夜陪聊", "max_level": 3, "unlock_at": 50},
                {"name": "保守秘密", "max_level": 3, "unlock_at": 50},
            ],
        },
        "闺蜜/老铁": {
            "level": 4,
            "skills": [
                {"name": "互怼", "max_level": 3, "unlock_at": 100},
                {"name": "学习建议", "max_level": 5, "unlock_at": 100},
            ],
        },
        "灵魂搭档": {
            "level": 5,
            "skills": [
                {"name": "精准惊喜", "max_level": 3, "unlock_at": 200},
                {"name": "成长陪伴", "max_level": 5, "unlock_at": 200},
            ],
        },
    }

    LEVEL_THRESHOLDS = [0, 20, 50, 100, 200]

    def __init__(self, user_id: str, xiaoman_dir: str, user_dir: str):
        self.user_id = user_id
        self.xm_path = os.path.join(xiaoman_dir, "skills.json")
        self.u_path = os.path.join(user_dir, "skills.json")
        self._init_files()

    def _init_files(self):
        for path, template in [(self.xm_path, "xiaoman_skills.json"), (self.u_path, "user_skills.json")]:
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

    # ===== 小满技能 =====

    def get_xiaoman(self) -> dict[str, Any]:
        return self._load(self.xm_path)

    def get_tree_state(self) -> dict[str, Any]:
        """获取完整技能树状态"""
        data = self._load(self.xm_path)
        xp = data.get("xp", 0)
        current_level = 1
        for i, threshold in enumerate(self.LEVEL_THRESHOLDS):
            if xp >= threshold:
                current_level = i + 1

        level_names = ["", "新同桌", "饭搭子", "树洞", "闺蜜/老铁", "灵魂搭档"]
        next_threshold = self.LEVEL_THRESHOLDS[current_level] if current_level < 5 else 9999

        return {
            "level": current_level,
            "name": level_names[current_level],
            "xp": xp,
            "next_threshold": next_threshold,
            "progress": (xp - self.LEVEL_THRESHOLDS[current_level - 1]) / (next_threshold - self.LEVEL_THRESHOLDS[current_level - 1]) if current_level < 5 else 1.0,
            "unlocked_skills": data.get("unlocked", []),
            "learning_skills": data.get("learning", []),
        }

    def add_xp(self, amount: int) -> dict[str, Any]:
        """增加经验值，可能触发升级"""
        data = self._load(self.xm_path)
        old_xp = data.get("xp", 0)
        new_xp = old_xp + amount
        data["xp"] = new_xp

        # 检查升级
        old_level = 1
        new_level = 1
        for i, threshold in enumerate(self.LEVEL_THRESHOLDS):
            if old_xp >= threshold:
                old_level = i + 1
            if new_xp >= threshold:
                new_level = i + 1

        # 解锁新技能
        if new_level > old_level:
            level_names = ["", "新同桌", "饭搭子", "树洞", "闺蜜/老铁", "灵魂搭档"]
            new_level_name = level_names[new_level]
            new_skills = self.SKILL_TREE.get(new_level_name, {}).get("skills", [])
            for skill in new_skills:
                data.setdefault("unlocked", [])
                if not any(s["name"] == skill["name"] for s in data["unlocked"]):
                    data["unlocked"].append({
                        "name": skill["name"],
                        "level": 1,
                        "max_level": skill["max_level"],
                    })

        self._save(self.xm_path, data)
        return {"old_level": old_level, "new_level": new_level, "xp_gained": amount}

    def unlock(self, skill_name: str) -> bool:
        """手动解锁一个技能"""
        data = self._load(self.xm_path)
        data.setdefault("unlocked", [])
        if not any(s["name"] == skill_name for s in data["unlocked"]):
            data["unlocked"].append({"name": skill_name, "level": 1, "max_level": 3})
            self._save(self.xm_path, data)
            return True
        return False

    def update_learning_progress(self, skill_name: str, progress: float):
        data = self._load(self.xm_path)
        data.setdefault("learning", [])
        for item in data["learning"]:
            if item["name"] == skill_name:
                item["progress"] = min(1.0, item.get("progress", 0) + progress)
                break
        else:
            data["learning"].append({"name": skill_name, "progress": progress, "target": 1.0})
        self._save(self.xm_path, data)

    def update_for_grade(self, grade: int):
        """年级变化时更新知识领域"""
        data = self._load(self.xm_path)
        if grade >= 10:
            # 高中增加理科内容
            if "物理难题" not in data.get("weaknesses", []):
                data.setdefault("weaknesses", []).append("物理难题")
        self._save(self.xm_path, data)

    # ===== 用户技能 =====

    def get_user(self) -> dict[str, Any]:
        return self._load(self.u_path)

    def set_user_subject_strength(self, subject: str, level: str):
        data = self._load(self.u_path)
        data.setdefault("subject_strengths", {})[subject] = level
        self._save(self.u_path, data)

    def add_user_study_method(self, method: str):
        data = self._load(self.u_path)
        data.setdefault("study_methods", [])
        if method not in data["study_methods"]:
            data["study_methods"].append(method)
        self._save(self.u_path, data)

    def set_user_target_school(self, school: str):
        data = self._load(self.u_path)
        data["target_school"] = school
        self._save(self.u_path, data)

    def add_user_hobby(self, hobby: str):
        data = self._load(self.u_path)
        data.setdefault("hobbies_skills", [])
        if hobby not in data["hobbies_skills"]:
            data["hobbies_skills"].append(hobby)
        self._save(self.u_path, data)

    def add_user_knowledge_gap(self, gap: str):
        data = self._load(self.u_path)
        data.setdefault("knowledge_gaps", [])
        if gap not in data["knowledge_gaps"]:
            data["knowledge_gaps"].append(gap)
        self._save(self.u_path, data)
