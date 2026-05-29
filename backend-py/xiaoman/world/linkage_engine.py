"""联动链路引擎 — YAML 配置 + 硬编码兜底"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from xiaoman.world.linkage_config import (
    evaluate_triggers,
    load_linkage_definitions,
    resolve_conflicts,
)


class LinkageEngine:
    """8 层之间的连锁反应"""

    def __init__(self, world_system):
        self.world = world_system
        self.definitions = load_linkage_definitions()
        self.prompt_hints: list[str] = []
        self.last_results: list[dict[str, Any]] = []

    def evaluate(self, user_text: str, changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        self.prompt_hints = []
        triggered: list[tuple[Any, list[dict[str, Any]]]] = []

        xm_skills = self.world.l6_skills.get_xiaoman()
        relation_xp = int(xm_skills.get("xp", 0))
        user_schedule = self.world.l3_schedule.get_user()
        context = {
            "user_emotion": self.world.l5_emotion.get_user().get("current_emotion", ""),
            "hour": datetime.now().hour,
            "user_text": user_text,
            "relation_xp": relation_xp,
            "relation_level": self.world.get_relation_level(),
            "birthday_days_until": self._days_until_birthday(user_schedule.get("birthday")),
        }

        for defn in self.definitions:
            if evaluate_triggers(defn, user_text, changes, context):
                effects = self._execute_actions(defn, user_text, context)
                triggered.append((defn, effects))

        results: list[dict[str, Any]] = []
        if not triggered:
            results.extend(self._legacy_evaluate(user_text, changes, include_xp=False))
        else:
            resolved = resolve_conflicts(triggered)
            for defn, effects in resolved:
                for eff in effects:
                    results.append({"linkage": defn.name, **eff})

        results.extend(self._apply_dialogue_xp())
        self.last_results = results
        return results

    def _apply_dialogue_xp(self) -> list[dict[str, Any]]:
        """每轮对话增加 XP，可能触发关系升级（供 WebSocket skill_unlocked）"""
        xp_result = self.world.l6_skills.add_xp(1)
        if xp_result["new_level"] > xp_result["old_level"]:
            return [{
                "linkage": "dialogue→level_up",
                "old_level": xp_result["old_level"],
                "new_level": xp_result["new_level"],
                "result": f"关系升级 L{xp_result['old_level']}→L{xp_result['new_level']}",
            }]
        return []

    def get_prompt_hints(self) -> str:
        if not self.prompt_hints:
            return ""
        lines = "\n".join(f"- {h}" for h in self.prompt_hints)
        return f"【联动指引】\n{lines}\n\n"

    def _relation_meets_threshold(self, defn, context: dict[str, Any]) -> bool:
        min_xp = int(getattr(defn, "min_relation_xp", 0) or 0)
        if min_xp <= 0:
            return True
        return int(context.get("relation_xp", 0)) >= min_xp

    @staticmethod
    def _days_until_birthday(birthday: Any) -> int | None:
        if not birthday:
            return None
        from datetime import date

        today = date.today()
        try:
            if isinstance(birthday, str):
                bday = date.fromisoformat(birthday[:10])
            else:
                bday = birthday
            birthday_this_year = bday.replace(year=today.year)
            return (birthday_this_year - today).days
        except (ValueError, TypeError):
            return None

    def _execute_actions(self, defn, user_text: str, context: dict[str, Any]) -> list[dict[str, Any]]:
        effects: list[dict[str, Any]] = []
        full_intimacy = self._relation_meets_threshold(defn, context)
        secret_keywords = ["秘密", "只告诉你", "没告诉别人", "其实我一直"]

        for action in defn.actions:
            atype = action.get("type")

            if atype == "prompt_hint":
                if not full_intimacy:
                    continue
                hint = action.get("text", "")
                if hint:
                    self.prompt_hints.append(hint)
                    effects.append({"result": hint, "action": "prompt_hint"})

            elif atype == "update_state":
                if not full_intimacy and action.get("field") == "security_level":
                    continue
                target = action.get("target", "")
                value = action.get("value", "")
                if target == "xiaoman_emotion" and value:
                    self.world.l5_emotion.set_xiaoman_emotion(value, defn.name)
                    effects.append({"result": f"小满情绪→{value}", "action": "update_state"})
                elif action.get("field") == "security_level":
                    delta = int(action.get("delta", 0))
                    self.world.l5_emotion.update_xiaoman_security(delta)
                    effects.append({"result": f"安全感{delta:+d}", "action": "update_state"})

            elif atype == "store_secret":
                if any(w in user_text for w in secret_keywords):
                    self.world.l7_profile.add_secret(user_text[:200], action.get("level", "medium"))
                    result = "已记录秘密" if full_intimacy else "已记录秘密（关系尚浅，暂不深入回应）"
                    effects.append({"result": result, "action": "store_secret"})

            elif atype == "recall_memory":
                if not full_intimacy:
                    continue
                effects.append({
                    "result": action.get("query", "相关记忆"),
                    "action": "recall_memory",
                })

            elif atype == "log_event":
                event_type = action.get("event_type", "linkage")
                effects.append({"result": event_type, "action": "log_event"})
                self._write_life_log(defn.name, event_type, user_text)

        return effects

    def _write_life_log(self, linkage_name: str, event_type: str, user_text: str) -> None:
        try:
            from xiaoman.life_log import append_log

            preview = user_text.replace("\n", " ")[:48]
            append_log(
                self.world.user_id,
                event_type,
                f"联动 · {linkage_name}",
                source="linkage",
                detail=preview,
                meta={"linkage": linkage_name},
            )
        except Exception:
            pass

    def _legacy_evaluate(
        self,
        user_text: str,
        changes: list[dict[str, Any]],
        *,
        include_xp: bool = True,
    ) -> list[dict[str, Any]]:
        """无 YAML 匹配时的内置规则"""
        triggered = []
        for change in changes:
            layer = change.get("layer")
            change_type = change.get("change")
            if layer == "L2" and change_type == "weather_bad":
                self.world.l5_emotion.update_xiaoman_energy(-10)
                triggered.append({"linkage": "weather→emotion", "result": "小满因天气不好心情变差"})
            if layer == "L7" and change_type == "like_added":
                triggered.append({"linkage": "profile→memory", "result": f"记住喜好：{change.get('item', '')}"})

        user_emotion = self.world.l5_emotion.get_user().get("current_emotion", "")
        if user_emotion == "难过":
            self.world.l5_emotion.set_xiaoman_emotion("温柔", "用户难过")
            triggered.append({"linkage": "user_emotion→xiaoman_emotion", "result": "温柔陪伴模式"})
        elif user_emotion == "开心":
            self.world.l5_emotion.set_xiaoman_emotion("开心", "用户开心")
            triggered.append({"linkage": "user_emotion→xiaoman_emotion", "result": "一起开心"})

        if include_xp:
            triggered.extend(self._apply_dialogue_xp())
        return triggered
