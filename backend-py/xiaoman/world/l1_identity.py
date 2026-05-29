"""L1 核心身份层 — 小满 + 用户身份管理"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

GRADE_NAMES = {7: "初一", 8: "初二", 9: "初三", 10: "高一", 11: "高二", 12: "高三"}
ZODIAC_DATES = [
    ("摩羯座", (12, 22), (1, 19)), ("水瓶座", (1, 20), (2, 18)),
    ("双鱼座", (2, 19), (3, 20)), ("白羊座", (3, 21), (4, 19)),
    ("金牛座", (4, 20), (5, 20)), ("双子座", (5, 21), (6, 21)),
    ("巨蟹座", (6, 22), (7, 22)), ("狮子座", (7, 23), (8, 22)),
    ("处女座", (8, 23), (9, 22)), ("天秤座", (9, 23), (10, 23)),
    ("天蝎座", (10, 24), (11, 22)), ("射手座", (11, 23), (12, 21)),
]


def _get_zodiac(birthday: str) -> str:
    try:
        month, day = map(int, birthday.split("-"))
        for name, (s_m, s_d), (e_m, e_d) in ZODIAC_DATES:
            if (month == s_m and day >= s_d) or (month == e_m and day <= e_d):
                return name
    except Exception:
        pass
    return "双鱼座"


class IdentityLayer:
    """L1: 核心身份层"""

    def __init__(self, user_id: str, xiaoman_dir: str, user_dir: str):
        self.user_id = user_id
        self.xm_path = os.path.join(xiaoman_dir, "identity.json")
        self.u_path = os.path.join(user_dir, "identity.json")
        self._init_files()

    def _init_files(self):
        for path, template in [(self.xm_path, "xiaoman_identity.json"), (self.u_path, "user_identity.json")]:
            if not os.path.exists(path):
                template_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "templates", template)
                if os.path.exists(template_path):
                    with open(template_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if "xiaoman" in template:
                        data["id"] = f"XIAOMAN-{self.user_id}"
                        data["companion_code"] = companion_code_for_user(self.user_id)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self, path: str) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, path: str, data: dict[str, Any]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ===== 小满身份 =====

    def get_xiaoman(self) -> dict[str, Any]:
        data = self._load(self.xm_path)
        if not data.get("companion_code"):
            data["companion_code"] = companion_code_for_user(self.user_id)
            self._save(self.xm_path, data)
        return data

    def get_companion_code(self) -> str:
        return self.get_xiaoman().get("companion_code") or companion_code_for_user(self.user_id)

    def set_xiaoman_name(self, name: str):
        data = self._load(self.xm_path)
        data["custom_name"] = name
        data["name"] = name
        self._save(self.xm_path, data)

    def set_xiaoman_catchphrase(self, phrase: str):
        data = self._load(self.xm_path)
        data["catchphrase"] = phrase
        self._save(self.xm_path, data)

    def set_xiaoman_birthday(self, birthday: str):
        data = self._load(self.xm_path)
        data["birthday"] = birthday
        data["zodiac"] = _get_zodiac(birthday)
        self._save(self.xm_path, data)

    def update_trait(self, trait: str, value: int):
        data = self._load(self.xm_path)
        data.setdefault("personality_traits", {})[trait] = max(0, min(10, value))
        self._save(self.xm_path, data)

    def get_traits_display(self) -> dict[str, int]:
        """获取中文性格特质"""
        data = self._load(self.xm_path)
        traits = data.get("personality_traits", {})
        mapping = {
            "lively": "活泼",
            "empathetic": "善解人意",
            "sarcastic": "毒舌",
            "complaining": "爱吐槽",
            "affectionate": "会撒娇",
        }
        result = {}
        for k, v in traits.items():
            result[mapping.get(k, k)] = v
        return result

    # ===== 用户身份 =====

    def get_user(self) -> dict[str, Any]:
        return self._load(self.u_path)

    def set_user_name(self, name: str):
        data = self._load(self.u_path)
        data["name"] = name
        self._save(self.u_path, data)

    def set_user_grade(self, grade: int):
        data = self._load(self.u_path)
        data["grade"] = grade
        data["grade_name"] = GRADE_NAMES.get(grade, f"{grade}年级")
        self._save(self.u_path, data)
        # 同步小满年级
        self.sync_grade(grade)

    def set_user_art_style(self, style: str):
        data = self._load(self.u_path)
        data["art_style"] = style
        self._save(self.u_path, data)

    def set_user_gender(self, gender: str):
        data = self._load(self.u_path)
        data["gender"] = gender
        self._save(self.u_path, data)
        # 同步关系模式
        xm = self._load(self.xm_path)
        if gender == "male":
            xm["relationship_mode"] = "friend"
        else:
            xm["relationship_mode"] = "bestie"
        self._save(self.xm_path, xm)

    def set_user_school(self, school: str, class_name: str = ""):
        data = self._load(self.u_path)
        data["school"] = school
        if class_name:
            data["class"] = class_name
        self._save(self.u_path, data)

    def add_personality_tag(self, tag: str):
        data = self._load(self.u_path)
        data.setdefault("personality_tags", [])
        if tag not in data["personality_tags"]:
            data["personality_tags"].append(tag)
        self._save(self.u_path, data)

    def sync_grade(self, new_grade: int) -> dict[str, Any]:
        """年级同步：用户升级→小满同步升级"""
        xm = self._load(self.xm_path)
        old_grade = xm.get("grade", 8)
        xm["grade"] = new_grade
        xm["grade_name"] = GRADE_NAMES.get(new_grade, f"{new_grade}年级")
        self._save(self.xm_path, xm)
        return {
            "layer": "L1",
            "change": "grade_sync",
            "old": old_grade,
            "new": new_grade,
            "xiaoman_grade_name": xm["grade_name"],
        }


def companion_code_for_user(user_id: str) -> str:
    """存在层永久编号 — PRD #XM2026 形态"""
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:6].upper()
    return f"#XM{digest}"
