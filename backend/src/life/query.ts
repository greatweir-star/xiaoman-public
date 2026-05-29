/**
 * 小满状态查询器
 * 根据当前时间查询小满的状态、活动、心情
 * 用于对话生成时注入"活人感"
 */

import { getXiaomanState, getPeriodName, XiaomanPeriod } from "./schedule.js";
import { getTodayLog, DailyLog } from "./generator.js";

export interface XiaomanLifeContext {
  period: XiaomanPeriod;
  periodName: string;
  activity: string;
  energy: number;
  canChat: boolean;
  chatStyle: string;
  todayLog: DailyLog;
  currentMood: string;
}

export async function queryXiaomanLife(): Promise<XiaomanLifeContext> {
  const state = getXiaomanState();
  const todayLog = await getTodayLog();

  return {
    period: state.period,
    periodName: getPeriodName(state.period),
    activity: state.activity,
    energy: state.energy,
    canChat: state.canChat,
    chatStyle: state.chatStyle,
    todayLog,
    currentMood: todayLog.currentMood,
  };
}

// 格式化生活状态为文本（用于 Prompt 注入）
export function formatLifeContext(ctx: XiaomanLifeContext): string {
  if (!ctx.canChat) {
    return `\n【小满状态】\n小满正在${ctx.activity}，暂时无法聊天。`;
  }

  let text = `\n【小满状态】\n现在小满正在${ctx.activity}，精力值${ctx.energy}/100，心情${ctx.currentMood}。`;

  if (ctx.todayLog.breakfast) {
    text += `\n今天早餐：${ctx.todayLog.breakfast}。`;
  }

  if (ctx.todayLog.morningEvents.length > 0) {
    text += `\n上午：${ctx.todayLog.morningEvents.join("，")}。`;
  }

  if (ctx.todayLog.lunch) {
    text += `\n午饭：${ctx.todayLog.lunch}。`;
  }

  if (ctx.todayLog.afternoonEvents.length > 0) {
    text += `\n下午：${ctx.todayLog.afternoonEvents.join("，")}。`;
  }

  return text;
}
