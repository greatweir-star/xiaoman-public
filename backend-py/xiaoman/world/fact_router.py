"""将结构化事实路由到 8 层世界模型"""

from __future__ import annotations

import re
from typing import Any

from xiaoman.world.world_system import WorldSystem

CATEGORY_LAYER_MAP = {
    "identity": "L1",
    "preference": "L7",
    "event": "L8",
    "emotion": "L5",
    "relation": "L4",
    "interest": "L7",
    "schedule": "L3",
    "general": "L7",
}


def apply_facts_to_world(world: WorldSystem, facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把提取的事实写入对应层，返回产生的 change 列表"""
    changes: list[dict[str, Any]] = []

    for fact in facts:
        content = (fact.get("content") or fact.get("fact") or "").strip()
        if not content or len(content) < 2:
            continue

        category = fact.get("category", "general")
        layer = fact.get("layer") or CATEGORY_LAYER_MAP.get(category, "L7")

        from xiaoman.memory.user_name import extract_name_from_text

        extracted = extract_name_from_text(content)
        if extracted:
            world.l1_identity.set_user_name(extracted)
            world.l7_profile.set_xiaoman_name_for_user(extracted)
            changes.append({"layer": "L1", "change": "name_set", "value": extracted})

        if layer == "L1" or category == "identity":
            name_match = re.search(r"(?:叫|名字是|我是)([\u4e00-\u9fa5a-zA-Z]{1,8})", content)
            if name_match and not extracted:
                world.l1_identity.set_user_name(name_match.group(1))
                world.l7_profile.set_xiaoman_name_for_user(name_match.group(1))
                changes.append({"layer": "L1", "change": "name_set", "value": name_match.group(1)})

        elif layer == "L4" or category == "relation":
            if any(w in content for w in ["朋友", "同学", "暗恋", "喜欢"]):
                changes.append({"layer": "L4", "change": "relation_mentioned", "content": content})

        elif layer == "L5" or category == "emotion":
            world.l7_profile.add_emotion_pattern(content)
            changes.append({"layer": "L5", "change": "emotion_fact", "content": content})

        elif layer == "L3" or category == "schedule":
            if any(w in content for w in ["考试", "月考", "期中", "期末"]):
                world.l3_schedule.add_user_exam(content[:30], "")
                changes.append({"layer": "L3", "change": "exam_added", "content": content})
            if "作业" in content:
                status = "很多" if any(w in content for w in ["多", "写不完"]) else "进行中"
                world.l3_schedule.set_user_homework(status)
                changes.append({"layer": "L3", "change": "homework_updated"})
            if any(w in content for w in ["睡", "起床", "作息"]):
                changes.append({"layer": "L3", "change": "routine_mentioned", "content": content})

        elif layer == "L7" or category in ("preference", "interest", "general"):
            if any(w in content for w in ["喜欢", "爱", "最爱"]):
                item = re.sub(r".*?(?:喜欢|爱|最爱)", "", content).strip(" ，。！")
                if item:
                    world.l7_profile.add_like(item)
                    changes.append({"layer": "L7", "change": "like_added", "item": item})
            elif any(w in content for w in ["讨厌", "不喜欢"]):
                item = re.sub(r".*?(?:讨厌|不喜欢)", "", content).strip(" ，。！")
                if item:
                    world.l7_profile.add_dislike(item)
                    changes.append({"layer": "L7", "change": "dislike_added", "item": item})
            else:
                world.l7_profile.add_exclusive_memory(content)
                changes.append({"layer": "L7", "change": "memory_added", "content": content})

    return changes
