"""WorldSystem — 小满双世界系统统一管理器"""

from __future__ import annotations

import json
import os
from typing import Any

from xiaoman.world.l1_identity import IdentityLayer
from xiaoman.world.l2_living_env import LivingEnvLayer
from xiaoman.world.l3_schedule import ScheduleLayer
from xiaoman.world.l4_social import SocialLayer
from xiaoman.world.l5_emotion import EmotionLayer
from xiaoman.world.l6_skills import SkillsLayer
from xiaoman.world.l7_profile import ProfileLayer
from xiaoman.world.l8_dialogue import DialogueLayer
from xiaoman.time_service import TimeService
from xiaoman.world.linkage_engine import LinkageEngine

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")

TIME_MODE_HINTS = {
    "night_chat": "深夜心事模式：语气更柔软，可聊心事",
    "relax": "放松模式：适合聊娱乐、吐槽",
    "morning_rush": "早高峰模式：回复简短",
    "after_school": "刚放学模式：可分享路上见闻",
    "normal": "",
}


class WorldSystem:
    """统一管理小满世界 + 用户世界的所有层级"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_data_dir = os.path.join(DATA_DIR, "users", user_id)
        os.makedirs(self.user_data_dir, exist_ok=True)

        self.xiaoman_dir = os.path.join(self.user_data_dir, "xiaoman")
        self.user_dir = os.path.join(self.user_data_dir, "user")
        os.makedirs(self.xiaoman_dir, exist_ok=True)
        os.makedirs(self.user_dir, exist_ok=True)

        # 初始化8层
        self.l1_identity = IdentityLayer(self.user_id, self.xiaoman_dir, self.user_dir)
        self.l2_living_env = LivingEnvLayer(self.user_id, self.xiaoman_dir, self.user_dir)
        self.l3_schedule = ScheduleLayer(self.user_id, self.xiaoman_dir, self.user_dir)
        self.l4_social = SocialLayer(self.user_id, self.xiaoman_dir, self.user_dir)
        self.l5_emotion = EmotionLayer(self.user_id, self.xiaoman_dir, self.user_dir)
        self.l6_skills = SkillsLayer(self.user_id, self.xiaoman_dir, self.user_dir)
        self.l7_profile = ProfileLayer(self.user_id, self.xiaoman_dir, self.user_dir)
        self.l8_dialogue = DialogueLayer(self.user_id, self.xiaoman_dir, self.user_dir)

        # 联动引擎
        self.linkage = LinkageEngine(self)
        self.time_service = TimeService()

    def get_relation_level(self) -> int:
        """关系等级 → 控制渐进 revealed（PRD memory-00）"""
        return int(self.l6_skills.get_tree_state().get("level", 1))

    def get_xiaoman_context(self) -> dict[str, Any]:
        """获取小满当前完整状态（用于注入Prompt）"""
        level = self.get_relation_level()
        emotion = self.l5_emotion.get_xiaoman()
        user_sched = self.l3_schedule.get_user()
        return {
            "identity": self.l1_identity.get_xiaoman(),
            "living_env": self.l2_living_env.get_xiaoman(),
            "schedule": self.l3_schedule.get_xiaoman(),
            "social": self.l4_social.get_xiaoman_visible(relation_level=level),
            "emotion": emotion,
            "energy": int(emotion.get("energy", 50)),
            "current_emotion": emotion.get("current_emotion", "平静"),
            "focus_session": user_sched.get("focus_session") or {"active": False},
            "skills": self.l6_skills.get_xiaoman(),
            "relation_level": level,
        }

    def get_user_context(self) -> dict[str, Any]:
        """获取用户当前完整状态"""
        return {
            "identity": self.l1_identity.get_user(),
            "living_env": self.l2_living_env.get_user(),
            "schedule": self.l3_schedule.get_user(),
            "social": self.l4_social.get_user(),
            "emotion": self.l5_emotion.get_user(),
            "skills": self.l6_skills.get_user(),
            "profile": self.l7_profile.get_user(),
            "understanding": self.l7_profile.get_xiaoman_understanding(),
        }

    def update_from_message(self, user_text: str, xiaoman_reply: str) -> list[dict[str, Any]]:
        """处理一条对话，更新世界状态并返回联动结果"""
        changes = []

        # 更新用户画像
        profile_changes = self.l7_profile.update_from_message(user_text)
        changes.extend(profile_changes)

        # 更新对话历史
        self.l8_dialogue.add_turn(user_text, xiaoman_reply)

        # 日程关键词（作业/考试）
        changes.extend(self._detect_schedule_from_text(user_text))

        # 天气关键词 → L2/L5 联动
        changes.extend(self._detect_weather_from_text(user_text))

        # 检测情绪
        emotion_changes = self.l5_emotion.detect_user_emotion(user_text)
        changes.extend(emotion_changes)

        # 更新小满情绪（根据用户情绪联动）
        xiaoman_changes = self.l5_emotion.update_xiaoman_from_user(user_text)
        changes.extend(xiaoman_changes)

        # 每轮精力衰减（L5 写回）
        from xiaoman.dialogue.period import get_school_period

        period_info = get_school_period()
        decay = self.l5_emotion.apply_turn_energy_decay(
            period=period_info.period,
            in_class=period_info.in_class,
        )
        changes.append(decay)

        # 关系层情感日记（轻量：强情绪轮次追加一行）
        self._maybe_append_emotional_diary(user_text, xiaoman_reply)

        # 更新社交关系
        social_changes = self.l4_social.update_from_message(user_text)
        changes.extend(social_changes)

        linkage_changes = self.linkage.evaluate(user_text, changes)
        return linkage_changes

    def _maybe_append_emotional_diary(self, user_text: str, xiaoman_reply: str) -> None:
        """关系层轻量情感日记 — vent/强情绪时追加 diary.jsonl 一行。"""
        from datetime import date

        from xiaoman.dialogue.input_parser import parse_user_input

        parsed = parse_user_input(user_text)
        strong = ("难过", "哭", "焦虑", "压力", "开心", "耶", "烦")
        triggered = (
            parsed.intent == "vent"
            or parsed.message_type == "emotion"
            or any(w in user_text for w in strong)
        )
        if not triggered:
            return
        today = date.today().isoformat()
        preview = user_text.replace("\n", " ")[:36]
        snippet = xiaoman_reply.replace("\n", " ")[:48]
        line = f"今天聊到「{preview}」，我回：{snippet}"
        entries = self.l8_dialogue.get_diary(today)
        if any(line[:30] in (e.get("content") or "") for e in entries):
            return
        self.l8_dialogue.add_diary_entry(today, line, kind="emotional")
        try:
            from xiaoman.life_log import append_log

            append_log(
                self.user_id,
                "emotional_diary",
                f"情感日记 · {preview}",
                source="diary",
                detail=line,
                meta={"date": today, "kind": "emotional"},
            )
        except Exception:
            pass

    def _detect_schedule_from_text(self, user_text: str) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        if "作业" in user_text:
            if any(w in user_text for w in ["写完", "做完", "完成了", "搞定了"]):
                self.l3_schedule.set_user_homework("已完成")
                changes.append({"layer": "L3", "change": "homework_done"})
            elif any(w in user_text for w in ["好多", "很多", "写不完"]):
                self.l3_schedule.set_user_homework("很多")
                changes.append({"layer": "L3", "change": "homework_heavy"})
        if "考试" in user_text or "月考" in user_text or "期中" in user_text:
            changes.append({"layer": "L3", "change": "exam_mentioned"})
        if "生日" in user_text and any(w in user_text for w in ["下周", "明天", "后天"]):
            changes.append({"layer": "L3", "change": "birthday_mentioned"})
        return changes

    def _detect_weather_from_text(self, user_text: str) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        if "下雨" in user_text:
            result = self.l2_living_env.update_weather("今天下雨")
            delta = result.get("emotion_delta")
            if isinstance(delta, int):
                self.l5_emotion.update_xiaoman_energy(delta)
            changes.append(result)
        elif "晴天" in user_text or "大太阳" in user_text:
            changes.append(self.l2_living_env.update_weather("今天大晴天"))
        return changes

    def get_linkage_prompt_hints(self) -> str:
        return self.linkage.get_prompt_hints()

    def get_life_context_for_prompt(self) -> str:
        """生成小满生活化状态文本（注入System Prompt）"""
        parts = [self.time_service.format_for_prompt(self.l3_schedule.get_user())]

        time_mode = self.l3_schedule.get_time_mode()
        mode_hint = TIME_MODE_HINTS.get(time_mode, "")
        if mode_hint:
            parts.append(f"【场景模式】{mode_hint}")

        schedule = self.l3_schedule.get_xiaoman()
        parts.append(f"【此刻状态】{schedule.get('current_activity', '空闲')}")

        # 情绪状态
        emotion = self.l5_emotion.get_xiaoman()
        parts.append(f"【我的心情】{emotion.get('current_emotion', '平静')}，精力{emotion.get('energy', 50)}%")

        # 环境状态
        env = self.l2_living_env.get_xiaoman()
        weather = env.get("current_weather", "")
        if weather:
            parts.append(f"【天气】{weather}")
        else:
            season = self.time_service.get_time_context().season
            season_cn = {"spring": "春天", "summer": "夏天", "autumn": "秋天", "winter": "冬天"}.get(season, "")
            if season_cn and env.get("season_preference"):
                parts.append(f"【季节】{season_cn}（{env['season_preference']}）")

        # 日程提醒
        countdown = schedule.get("countdown", {})
        if countdown.get("days_left", 0) > 0:
            parts.append(f"【倒计时】距离{countdown['event']}还有{countdown['days_left']}天")

        user_sched = self.l3_schedule.get_user()
        if user_sched.get("homework_status"):
            parts.append(f"【用户作业】{user_sched['homework_status']}")

        return "\n".join(parts)

    def get_dialogue_context_for_prompt(self) -> str:
        """L8 中期记忆摘要 — 约定、烦恼、共同梗"""
        mid = self.l8_dialogue.get_mid_term()
        lines: list[str] = []
        pacts = mid.get("unfinished_pacts") or []
        if pacts:
            lines.append(f"未完成约定：{pacts[-1].get('content', '')[:80]}")
        worries = mid.get("recent_worries") or []
        if worries:
            lines.append(f"近期烦恼：{worries[-1].get('content', '')[:80]}")
        jokes = mid.get("inside_jokes") or []
        if jokes:
            lines.append(f"共同梗：{jokes[-1].get('content', '')[:50]}")
        topics = mid.get("weekly_topics") or []
        if topics:
            lines.append(f"本周聊过：{topics[-1].get('topic', '')[:30]}")
        if not lines:
            return ""
        return "【对话延续】\n" + "\n".join(lines)

    def get_revealed_social_prompt(self) -> str:
        """渐进解锁：仅注入当前关系等级可见的小满社交信息"""
        level = self.get_relation_level()
        visible = self.l4_social.get_xiaoman_visible(relation_level=level)
        if not visible:
            return ""
        lines = [f"【小满社交·Lv{level}可见】"]
        if visible.get("deskmate"):
            lines.append(f"同桌：{visible['deskmate'].get('name', '未知')}")
        if visible.get("family"):
            lines.append(f"家人：{len(visible['family'])}人")
        if visible.get("besties"):
            names = [b.get("name", "") for b in visible["besties"][:2]]
            lines.append(f"闺蜜：{', '.join(n for n in names if n)}")
        if visible.get("crush"):
            lines.append("有暗恋对象（关系足够深才与你聊）")
        return "\n".join(lines) if len(lines) > 1 else ""

    def advance_grade(self, new_grade: int) -> dict[str, Any]:
        """用户升级时同步更新"""
        result = self.l1_identity.sync_grade(new_grade)
        self.l3_schedule.update_for_grade(new_grade)
        self.l6_skills.update_for_grade(new_grade)
        return result

    def get_skill_tree(self) -> dict[str, Any]:
        """获取技能树完整数据"""
        return self.l6_skills.get_tree_state()

    def unlock_skill(self, skill_name: str) -> bool:
        """解锁一个技能"""
        return self.l6_skills.unlock(skill_name)

    def get_diary(self, date: str | None = None) -> list[dict[str, Any]]:
        """获取日记"""
        return self.l8_dialogue.get_diary(date)

    def get_social_graph(self, side: str = "xiaoman") -> dict[str, Any]:
        """获取社交关系图"""
        if side == "xiaoman":
            return self.l4_social.get_xiaoman()
        return self.l4_social.get_user()

    def to_dict(self) -> dict[str, Any]:
        """导出完整世界状态"""
        return {
            "xiaoman": {
                "identity": self.l1_identity.get_xiaoman(),
                "living_env": self.l2_living_env.get_xiaoman(),
                "schedule": self.l3_schedule.get_xiaoman(),
                "social": self.l4_social.get_xiaoman(),
                "emotion": self.l5_emotion.get_xiaoman(),
                "skills": self.l6_skills.get_xiaoman(),
            },
            "user": {
                "identity": self.l1_identity.get_user(),
                "living_env": self.l2_living_env.get_user(),
                "schedule": self.l3_schedule.get_user(),
                "social": self.l4_social.get_user(),
                "emotion": self.l5_emotion.get_user(),
                "skills": self.l6_skills.get_user(),
                "profile": self.l7_profile.get_user(),
                "dialogue": self.l8_dialogue.get_stats(),
            },
        }
