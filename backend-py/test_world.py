from xiaoman.world import WorldSystem

w = WorldSystem('test_user_001')
print('L1 identity:', w.l1_identity.get_xiaoman().get('name'))
print('L3 schedule activity:', w.l3_schedule.get_xiaoman().get('current_activity'))
print('L5 emotion:', w.l5_emotion.get_xiaoman().get('current_emotion'))
print('Skill tree:', w.get_skill_tree().get('name'))
print('World context:', w.get_life_context_for_prompt()[:50])

# 测试联动
changes = w.update_from_message("我今天数学考砸了，好烦", "别难过，下次加油")
print('Linkage changes:', changes)

# 测试用户情绪检测
print('User emotion:', w.l5_emotion.get_user().get('current_emotion'))
print('Xiaoman emotion:', w.l5_emotion.get_xiaoman().get('current_emotion'))

# 测试技能树XP
print('Skill tree after chat:', w.get_skill_tree())
