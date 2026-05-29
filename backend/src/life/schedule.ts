/**
 * 小满生活时间表 + 状态机
 * 根据当前时间返回小满的状态、活动、精力
 */

export type XiaomanPeriod =
  | "sleep"
  | "morning"
  | "class"
  | "lunch"
  | "after_class"
  | "dinner"
  | "homework"
  | "bedtime";

interface ScheduleEntry {
  period: XiaomanPeriod;
  startHour: number;
  startMinute: number;
  endHour: number;
  endMinute: number;
  activity: string;
  energy: number; // 0-100
  canChat: boolean; // 是否能聊天
  chatStyle: string; // 回复风格
}

// 工作日时间表
const WEEKDAY_SCHEDULE: ScheduleEntry[] = [
  { period: "sleep", startHour: 0, startMinute: 0, endHour: 6, endMinute: 30, activity: "睡觉", energy: 0, canChat: false, chatStyle: "拒绝回复" },
  { period: "morning", startHour: 6, startMinute: 30, endHour: 8, endMinute: 0, activity: "起床洗漱，准备上学", energy: 70, canChat: true, chatStyle: "元气但匆忙" },
  { period: "class", startHour: 8, startMinute: 0, endHour: 12, endMinute: 0, activity: "上课", energy: 50, canChat: true, chatStyle: "偷偷回复，简短" },
  { period: "lunch", startHour: 12, startMinute: 0, endHour: 14, endMinute: 0, activity: "午饭+午休", energy: 75, canChat: true, chatStyle: "放松活泼" },
  { period: "class", startHour: 14, startMinute: 0, endHour: 17, endMinute: 30, activity: "上课", energy: 45, canChat: true, chatStyle: "疲惫简短" },
  { period: "after_class", startHour: 17, startMinute: 30, endHour: 18, endMinute: 30, activity: "放学路上", energy: 80, canChat: true, chatStyle: "开心话多" },
  { period: "dinner", startHour: 18, startMinute: 30, endHour: 19, endMinute: 30, activity: "吃晚饭", energy: 70, canChat: true, chatStyle: "家常温暖" },
  { period: "homework", startHour: 19, startMinute: 30, endHour: 22, endMinute: 0, activity: "写作业", energy: 55, canChat: true, chatStyle: "专注偶尔抱怨" },
  { period: "bedtime", startHour: 22, startMinute: 0, endHour: 22, endMinute: 30, activity: "洗漱准备睡觉", energy: 40, canChat: true, chatStyle: "慵懒温柔" },
  { period: "sleep", startHour: 22, startMinute: 30, endHour: 23, endMinute: 59, activity: "睡觉", energy: 0, canChat: false, chatStyle: "拒绝回复" },
];

// 周末时间表
const WEEKEND_SCHEDULE: ScheduleEntry[] = [
  { period: "sleep", startHour: 0, startMinute: 0, endHour: 9, endMinute: 0, activity: "睡懒觉", energy: 0, canChat: false, chatStyle: "拒绝回复" },
  { period: "morning", startHour: 9, startMinute: 0, endHour: 12, endMinute: 0, activity: "起床+写作业", energy: 75, canChat: true, chatStyle: "慵懒随意" },
  { period: "lunch", startHour: 12, startMinute: 0, endHour: 14, endMinute: 0, activity: "午饭", energy: 80, canChat: true, chatStyle: "放松" },
  { period: "after_class", startHour: 14, startMinute: 0, endHour: 18, endMinute: 0, activity: "出去玩/补课", energy: 85, canChat: true, chatStyle: "开心活泼" },
  { period: "dinner", startHour: 18, startMinute: 0, endHour: 19, endMinute: 30, activity: "晚饭", energy: 75, canChat: true, chatStyle: "家常" },
  { period: "homework", startHour: 19, startMinute: 30, endHour: 22, endMinute: 0, activity: "写作业/刷手机", energy: 60, canChat: true, chatStyle: "随意" },
  { period: "bedtime", startHour: 22, startMinute: 0, endHour: 23, endMinute: 0, activity: "准备睡觉", energy: 45, canChat: true, chatStyle: "慵懒" },
  { period: "sleep", startHour: 23, startMinute: 0, endHour: 23, endMinute: 59, activity: "睡觉", energy: 0, canChat: false, chatStyle: "拒绝回复" },
];

function isWeekend(date: Date): boolean {
  const day = date.getDay();
  return day === 0 || day === 6;
}

function timeToMinutes(hour: number, minute: number): number {
  return hour * 60 + minute;
}

export function getCurrentSchedule(date: Date = new Date()): ScheduleEntry {
  const schedule = isWeekend(date) ? WEEKEND_SCHEDULE : WEEKDAY_SCHEDULE;
  const currentMinutes = timeToMinutes(date.getHours(), date.getMinutes());

  for (const entry of schedule) {
    const start = timeToMinutes(entry.startHour, entry.startMinute);
    const end = timeToMinutes(entry.endHour, entry.endMinute);
    if (currentMinutes >= start && currentMinutes < end) {
      return entry;
    }
  }

  // 默认返回睡眠时间
  return schedule[0];
}

export function getXiaomanState(date: Date = new Date()) {
  const schedule = getCurrentSchedule(date);
  return {
    period: schedule.period,
    activity: schedule.activity,
    energy: schedule.energy,
    canChat: schedule.canChat,
    chatStyle: schedule.chatStyle,
  };
}

// 获取时段中文名
export function getPeriodName(period: XiaomanPeriod): string {
  const names: Record<XiaomanPeriod, string> = {
    sleep: "睡觉",
    morning: "早晨",
    class: "上课",
    lunch: "午饭",
    after_class: "放学",
    dinner: "晚饭",
    homework: "写作业",
    bedtime: "睡前",
  };
  return names[period];
}
