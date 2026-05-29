"""L3 时间日程层 — 小满 + 用户时间日程"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any


class ScheduleLayer:
    """L3: 时间日程层"""

    def __init__(self, user_id: str, xiaoman_dir: str, user_dir: str):
        self.user_id = user_id
        self.xm_path = os.path.join(xiaoman_dir, "schedule.json")
        self.u_path = os.path.join(user_dir, "schedule.json")
        self._init_files()

    def _init_files(self):
        for path, template in [(self.xm_path, "xiaoman_schedule.json"), (self.u_path, "user_schedule.json")]:
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

    # ===== 小满日程 =====

    def get_xiaoman(self) -> dict[str, Any]:
        data = self._load(self.xm_path)
        data["current_activity"] = self._calc_current_activity(data)
        self._update_countdown(data)
        return data

    def _calc_current_activity(self, data: dict) -> str:
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        current_time = hour * 60 + minute

        routine = data.get("daily_routine", {})
        activities = []
        for time_str, activity in routine.items():
            try:
                h, m = map(int, time_str.split(":"))
                t = h * 60 + m
                activities.append((t, activity))
            except Exception:
                continue
        activities.sort(key=lambda x: x[0])

        current = activities[0][1] if activities else "空闲"
        for i, (t, activity) in enumerate(activities):
            if current_time >= t:
                current = activity
            else:
                break
        return current

    def _update_countdown(self, data: dict):
        countdown = data.get("countdown", {})
        if countdown.get("date"):
            try:
                target = datetime.strptime(countdown["date"], "%Y-%m-%d")
                days_left = (target - datetime.now()).days
                countdown["days_left"] = max(0, days_left)
            except Exception:
                pass

    def set_routine(self, routine: dict[str, str]):
        data = self._load(self.xm_path)
        data["daily_routine"] = routine
        self._save(self.xm_path, data)

    def set_week_schedule(self, week: dict[str, list[str]]):
        data = self._load(self.xm_path)
        data["week_schedule"] = week
        self._save(self.xm_path, data)

    def set_countdown(self, event: str, date: str):
        data = self._load(self.xm_path)
        data["countdown"] = {"event": event, "date": date, "days_left": 0}
        self._save(self.xm_path, data)

    def update_for_grade(self, grade: int):
        """年级变化时更新课程表"""
        data = self._load(self.xm_path)
        # 根据年级调整作息
        if grade >= 10:  # 高中
            data["daily_routine"] = {
                "06:30": "起床",
                "07:00": "出门",
                "08:00": "早读",
                "12:00": "午饭",
                "14:00": "下午课",
                "18:00": "晚自习",
                "22:00": "回家",
                "23:30": "睡觉"
            }
        self._save(self.xm_path, data)

    # ===== 用户日程 =====

    def get_user(self) -> dict[str, Any]:
        return self._load(self.u_path)

    def set_user_sleep_time(self, sleep: str, wake: str):
        data = self._load(self.u_path)
        data["sleep_time"] = sleep
        data["wake_time"] = wake
        self._save(self.u_path, data)

    def set_user_homework(self, status: str):
        data = self._load(self.u_path)
        data["homework_status"] = status
        self._save(self.u_path, data)

    def add_user_exam(self, exam: str, date: str):
        data = self._load(self.u_path)
        data.setdefault("upcoming_exams", [])
        data["upcoming_exams"].append({"name": exam, "date": date})
        self._save(self.u_path, data)

    def set_user_free_time(self, free_time: str):
        data = self._load(self.u_path)
        data["free_time"] = free_time
        self._save(self.u_path, data)

    def add_special_date(self, name: str, date: str):
        data = self._load(self.u_path)
        data.setdefault("special_dates", [])
        data["special_dates"].append({"name": name, "date": date})
        self._save(self.u_path, data)

    def add_pending_reminder(self, text: str):
        data = self._load(self.u_path)
        data.setdefault("pending_reminders", [])
        if text and text not in data["pending_reminders"]:
            data["pending_reminders"].append(text)
        self._save(self.u_path, data)

    def set_focus_session(self, *, task: str, ends_at: str, minutes: int):
        data = self._load(self.u_path)
        data["focus_session"] = {
            "active": True,
            "task": task,
            "ends_at": ends_at,
            "minutes": minutes,
            "started_at": datetime.now().isoformat(),
        }
        self._save(self.u_path, data)

    def get_focus_session(self) -> dict[str, Any]:
        data = self._load(self.u_path)
        return data.get("focus_session") or {"active": False}

    def focus_minutes_remaining(self) -> int:
        focus = self.get_focus_session()
        if not focus.get("active"):
            return 0
        ends_at = focus.get("ends_at")
        if not ends_at:
            return 0
        try:
            end = datetime.fromisoformat(ends_at)
            delta = (end - datetime.now()).total_seconds() / 60
            if delta <= 0:
                self.clear_focus_session()
                return 0
            return max(1, int(delta + 0.5))
        except ValueError:
            return 0

    def clear_focus_session(self):
        data = self._load(self.u_path)
        data["focus_session"] = {"active": False}
        self._save(self.u_path, data)

    def get_time_mode(self) -> str:
        """判断当前时间模式"""
        hour = datetime.now().hour
        if 23 <= hour or hour < 6:
            return "night_chat"
        elif 21 <= hour < 23:
            return "relax"
        elif 6 <= hour < 8:
            return "morning_rush"
        elif 17 <= hour < 19:
            return "after_school"
        return "normal"
