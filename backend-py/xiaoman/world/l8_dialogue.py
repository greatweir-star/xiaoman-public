"""L8 对话历史层 — 短期/中期/长期记忆"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timedelta
from typing import Any


class DialogueLayer:
    """L8: 对话历史层"""

    def __init__(self, user_id: str, xiaoman_dir: str, user_dir: str):
        self.user_id = user_id
        self.mid_term_path = os.path.join(user_dir, "mid_term_memory.json")
        self.long_term_path = os.path.join(user_dir, "long_term_memory.json")
        self.diary_path = os.path.join(xiaoman_dir, "diary.jsonl")
        self._init_files()

    def _init_files(self):
        for path in [self.mid_term_path, self.long_term_path]:
            if not os.path.exists(path):
                default = {
                    "weekly_topics": [],
                    "inside_jokes": [],
                    "unfinished_pacts": [],
                    "recent_worries": [],
                } if "mid" in path else {
                    "important_events": [],
                    "growth_milestones": [],
                    "relationship_milestones": [],
                    "high_frequency_topics": [],
                }
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(default, f, ensure_ascii=False, indent=2)

    def _load(self, path: str) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, path: str, data: dict[str, Any]):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ===== 中期记忆 =====

    def add_turn(self, user_text: str, xiaoman_reply: str):
        """记录一轮对话"""
        # 更新本周话题
        mid = self._load(self.mid_term_path)
        mid.setdefault("weekly_topics", [])
        topic = self._extract_topic(user_text)
        if topic:
            mid["weekly_topics"].append({
                "topic": topic,
                "date": datetime.now().isoformat(),
            })
            # 只保留最近7天
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            mid["weekly_topics"] = [t for t in mid["weekly_topics"] if t["date"] > cutoff]

        # 检测共同梗
        if any(w in user_text for w in ["哈哈", "笑死", "绝了"]):
            mid.setdefault("inside_jokes", [])
            mid["inside_jokes"].append({
                "content": user_text[:50],
                "date": datetime.now().isoformat(),
            })

        # 检测未完成约定
        if any(w in user_text for w in ["明天", "下次", "以后", "改天"]):
            mid.setdefault("unfinished_pacts", [])
            mid["unfinished_pacts"].append({
                "content": user_text[:100],
                "date": datetime.now().isoformat(),
            })

        # 检测近期烦恼
        worry_keywords = ["烦", "累", "焦虑", "担心", "压力", "难过"]
        if any(w in user_text for w in worry_keywords):
            mid.setdefault("recent_worries", [])
            mid["recent_worries"].append({
                "content": user_text[:100],
                "date": datetime.now().isoformat(),
            })
            # 只保留最近30天
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            mid["recent_worries"] = [w for w in mid["recent_worries"] if w["date"] > cutoff]

        self._save(self.mid_term_path, mid)

        # 更新长期记忆（高频话题统计）
        self._update_long_term(topic)

    def _extract_topic(self, text: str) -> str:
        """简单提取话题关键词"""
        # 取前10个字作为话题
        text = text.strip()
        if len(text) <= 10:
            return text
        return text[:10] + "..."

    def _update_long_term(self, topic: str | None):
        if not topic:
            return
        long_term = self._load(self.long_term_path)
        long_term.setdefault("high_frequency_topics", [])

        # 统计话题频率
        all_topics = [t["topic"] for t in long_term.get("high_frequency_topics", [])]
        all_topics.append(topic)
        counter = Counter(all_topics)

        # 保留高频话题
        frequent = [{"topic": t, "count": c} for t, c in counter.most_common(20)]
        long_term["high_frequency_topics"] = frequent
        self._save(self.long_term_path, long_term)

    def add_important_event(self, event: str, event_type: str):
        long_term = self._load(self.long_term_path)
        long_term.setdefault("important_events", [])
        long_term["important_events"].append({
            "event": event,
            "type": event_type,
            "date": datetime.now().isoformat(),
        })
        self._save(self.long_term_path, long_term)

    def add_growth_milestone(self, milestone: str):
        long_term = self._load(self.long_term_path)
        long_term.setdefault("growth_milestones", [])
        long_term["growth_milestones"].append({
            "milestone": milestone,
            "date": datetime.now().isoformat(),
        })
        self._save(self.long_term_path, long_term)

    def add_relationship_milestone(self, milestone: str):
        long_term = self._load(self.long_term_path)
        long_term.setdefault("relationship_milestones", [])
        long_term["relationship_milestones"].append({
            "milestone": milestone,
            "date": datetime.now().isoformat(),
        })
        self._save(self.long_term_path, long_term)

    def get_mid_term(self) -> dict[str, Any]:
        return self._load(self.mid_term_path)

    def get_long_term(self) -> dict[str, Any]:
        return self._load(self.long_term_path)

    def get_stats(self) -> dict[str, Any]:
        mid = self._load(self.mid_term_path)
        long_term = self._load(self.long_term_path)
        return {
            "weekly_topics_count": len(mid.get("weekly_topics", [])),
            "inside_jokes_count": len(mid.get("inside_jokes", [])),
            "unfinished_pacts_count": len(mid.get("unfinished_pacts", [])),
            "recent_worries_count": len(mid.get("recent_worries", [])),
            "important_events_count": len(long_term.get("important_events", [])),
            "growth_milestones_count": len(long_term.get("growth_milestones", [])),
            "relationship_milestones_count": len(long_term.get("relationship_milestones", [])),
            "high_frequency_topics": long_term.get("high_frequency_topics", [])[:5],
        }

    # ===== 日记 =====

    def get_diary(self, date: str | None = None) -> list[dict[str, Any]]:
        if not os.path.exists(self.diary_path):
            return []
        entries = []
        with open(self.diary_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if date is None or entry.get("date") == date:
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue
        return entries

    def add_diary_entry(self, date: str, content: str, *, kind: str = "daily"):
        os.makedirs(os.path.dirname(self.diary_path), exist_ok=True)
        entry = {
            "date": date,
            "content": content,
            "kind": kind,
            "created_at": datetime.now().isoformat(),
        }
        with open(self.diary_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
