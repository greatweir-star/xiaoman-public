"""TimeService — PRD memory-03 §7.3 时间感知"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass
class TimeContext:
    period: str
    is_school_day: bool
    day_type: str
    days_to_weekend: int
    hour: int
    weekday: int
    season: str
    xiaoman_status: str


class TimeService:
    """时间服务：时段、上学日、季节、特殊日期提醒"""

    def get_time_context(self) -> TimeContext:
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()

        if 5 <= hour < 11:
            period, xiaoman_status = "morning", "刚起床，有点困"
        elif 11 <= hour < 14:
            period, xiaoman_status = "noon", "午休时间，在食堂吃饭"
        elif 14 <= hour < 18:
            period, xiaoman_status = "afternoon", "下午上课，有点累"
        elif 18 <= hour < 22:
            period, xiaoman_status = "evening", "晚自习/写作业"
        else:
            period, xiaoman_status = "night", "该睡觉了，但还在刷手机"

        is_school_day = weekday < 5
        return TimeContext(
            period=period,
            is_school_day=is_school_day,
            day_type="上学日" if is_school_day else "周末",
            days_to_weekend=(4 - weekday) % 7,
            hour=hour,
            weekday=weekday,
            season=self._get_season(now.month),
            xiaoman_status=xiaoman_status,
        )

    def check_special_dates(self, user_schedule: dict[str, Any]) -> list[str]:
        """考试倒计时、生日提醒（7 天内）"""
        today = date.today()
        alerts: list[str] = []

        for exam in user_schedule.get("exams", []) or user_schedule.get("upcoming_exams", []):
            if isinstance(exam, dict):
                date_str = exam.get("date") or exam.get("exam_date", "")
                subject = exam.get("subject") or exam.get("name", "考试")
            else:
                continue
            if not date_str:
                continue
            try:
                exam_date = datetime.fromisoformat(str(date_str)[:10]).date()
                days_until = (exam_date - today).days
                if 0 <= days_until <= 7:
                    alerts.append(f"{subject}考试还有{days_until}天")
            except (ValueError, TypeError):
                continue

        birthday = user_schedule.get("birthday")
        if birthday:
            try:
                if isinstance(birthday, str):
                    bday = datetime.fromisoformat(birthday[:10]).date()
                else:
                    bday = birthday
                birthday_this_year = bday.replace(year=today.year)
                days_until = (birthday_this_year - today).days
                if 0 <= days_until <= 3:
                    alerts.append(f"生日还有{days_until}天")
            except (ValueError, TypeError):
                pass

        return alerts

    def format_for_prompt(self, user_schedule: dict[str, Any] | None = None) -> str:
        """生成可注入 Prompt 的时间上下文块"""
        ctx = self.get_time_context()
        parts = [
            f"【时间】{ctx.day_type} · {ctx.period} · {ctx.season}",
            f"【时段状态】{ctx.xiaoman_status}",
        ]
        if user_schedule:
            alerts = self.check_special_dates(user_schedule)
            if alerts:
                parts.append(f"【近期提醒】{'；'.join(alerts)}")
        return "\n".join(parts)

    @staticmethod
    def _get_season(month: int) -> str:
        if month in (3, 4, 5):
            return "spring"
        if month in (6, 7, 8):
            return "summer"
        if month in (9, 10, 11):
            return "autumn"
        return "winter"
