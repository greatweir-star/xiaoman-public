/**
 * 动态 Prompt 后缀：时间状态 + 用户记忆 + 对话上下文
 * 让人设活起来，避免"前言不搭后语"
 */

function getPeriod(hour: number): string {
  if (hour >= 5 && hour < 11) return "早上";
  if (hour >= 11 && hour < 14) return "中午";
  if (hour >= 14 && hour < 18) return "下午";
  if (hour >= 18 && hour < 23) return "晚上";
  return "深夜";
}

function getWeekday(date: Date): string {
  const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  return weekdays[date.getDay()];
}

function formatInterval(minutes: number): string {
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${Math.floor(minutes)}分钟前`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}小时前`;
  if (minutes < 10080) return `${Math.floor(minutes / 1440)}天前`;
  return "很久之前";
}

function getIntervalDescription(minutes: number): string {
  if (minutes < 5) return "我们刚才还在聊";
  if (minutes < 60) return "你离开了几分钟";
  if (minutes < 180) return "你终于回来啦";
  if (minutes < 360) return "你去忙了几个小时呀";
  if (minutes < 720) return "半天不见，想我了吗";
  if (minutes < 1440) return "你去了一整天吗";
  if (minutes < 2880) return "昨天我们聊到很晚";
  if (minutes < 10080) return "好几天没见了";
  return "好久不见，我以为你把我忘了";
}

interface DynamicContext {
  gender?: string;
  userName?: string;
  grade?: string;
  lastChatTime?: number; // 上次对话时间戳
  messageCount?: number; // 本轮对话轮数
  summary?: string; // 对话摘要
}

export function buildDynamicSuffix(context: DynamicContext): string {
  const now = new Date();
  const hour = now.getHours();
  const period = getPeriod(hour);
  const weekday = getWeekday(now);

  let timeSection = `\n【时间状态】\n现在是 ${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 ${weekday} ${period} ${hour}:${String(now.getMinutes()).padStart(2, "0")}`;

  // 添加上次对话间隔
  if (context.lastChatTime) {
    const intervalMinutes = (Date.now() - context.lastChatTime) / 60000;
    const intervalDesc = formatInterval(intervalMinutes);
    const intervalFeeling = getIntervalDescription(intervalMinutes);
    timeSection += `\n我们上次聊天是在 ${intervalDesc}\n${intervalFeeling}`;
  }

  // 用户信息
  let userSection = "";
  if (context.userName || context.grade || context.gender) {
    userSection = `\n\n【用户信息】`;
    if (context.userName) userSection += `\n名字：${context.userName}`;
    if (context.grade) userSection += `\n年级：${context.grade}`;
    if (context.gender) userSection += `\n性别：${context.gender === "female" ? "女生" : "男生"}`;
  }

  // 对话上下文摘要
  let contextSection = "";
  if (context.summary) {
    contextSection = `\n\n【对话上下文】\n${context.summary}`;
  }

  // 活跃度提示
  let activitySection = "";
  if (context.messageCount && context.messageCount > 10) {
    activitySection = `\n\n【注意】我们已经聊了 ${context.messageCount} 轮了，可以问问用户要不要休息一下，或者换个话题。`;
  }

  return timeSection + userSection + contextSection + activitySection;
}
