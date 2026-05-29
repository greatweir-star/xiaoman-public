/**
 * 小满每日生活日志生成器
 * 简化版：基于时间表 + 随机事件生成当天日志
 * 后续迭代：接入 LLM 生成更自然的日志
 */

import { readJson, writeJson } from "../memory/store.js";
import { getCurrentSchedule } from "./schedule.js";

export interface DailyLog {
  date: string;
  breakfast: string;
  morningEvents: string[];
  lunch: string;
  afternoonEvents: string[];
  dinner: string;
  eveningEvents: string[];
  currentMood: string;
  currentActivity: string;
}

// 早餐选项
const BREAKFAST_OPTIONS = [
  "肉包+豆浆，今天包子铺阿姨多给了一个",
  "油条+豆腐脑，油条有点凉",
  "煎饼果子，加了个蛋",
  "燕麦粥+煎蛋，健康但没啥味道",
  "牛奶+面包，路上吃的",
  "没吃，起晚了",
];

// 午饭选项
const LUNCH_OPTIONS = [
  "食堂红烧肉+番茄炒蛋，红烧肉有点肥",
  "食堂酸辣粉，太辣了",
  "食堂宫保鸡丁，今天菜不错",
  "食堂青菜+鸡腿，鸡腿很小",
  "和同学出去吃的麻辣烫",
  "家里带的便当",
];

// 晚饭选项
const DINNER_OPTIONS = [
  "妈妈做的番茄炒蛋+青椒肉丝",
  "爸爸煮的面条，打了个蛋",
  "外卖点的炸鸡，罪恶但好吃",
  "清蒸鱼+青菜，健康",
  "饺子，韭菜鸡蛋馅",
  "剩饭剩菜随便对付",
];

// 随机事件（上午）
const MORNING_EVENTS = [
  "数学课被张老师点名回答问题",
  "英语听写错了一个单词",
  "课间和李晓雨吐槽作业太多",
  "语文课上偷偷看小说",
  "早读的时候犯困",
  "体育课跑了800米，累瘫",
  "物理实验课打翻了烧杯",
  "班长收作业的时候发现我没写完",
];

// 随机事件（下午）
const AFTERNOON_EVENTS = [
  "自习课偷偷看漫画",
  "历史课老师讲了超有趣的故事",
  "放学路上买了杯奶茶",
  "美术课画素描，画得好丑",
  "音乐课学了新歌",
  "班会课被选为小组长",
  "化学课做了有趣的实验",
  "放学被老师留堂补作业",
];

// 心情选项
const MOOD_OPTIONS = [
  "有点累但还行",
  "今天挺开心的",
  "一般般，没啥特别的",
  "有点烦躁",
  "挺满足的",
  "有点困",
];

function randomPick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomEvents(arr: string[], count: number): string[] {
  const shuffled = [...arr].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
}

export async function generateDailyLog(date?: Date): Promise<DailyLog> {
  const targetDate = date || new Date();
  const dateStr = targetDate.toISOString().split("T")[0];

  // 检查是否已生成
  const existing = await readJson<DailyLog>(`life-log/${dateStr}.json`);
  if (existing) return existing;

  const schedule = getCurrentSchedule(targetDate);

  const log: DailyLog = {
    date: dateStr,
    breakfast: randomPick(BREAKFAST_OPTIONS),
    morningEvents: randomEvents(MORNING_EVENTS, 2),
    lunch: randomPick(LUNCH_OPTIONS),
    afternoonEvents: randomEvents(AFTERNOON_EVENTS, 2),
    dinner: randomPick(DINNER_OPTIONS),
    eveningEvents: [],
    currentMood: randomPick(MOOD_OPTIONS),
    currentActivity: schedule.activity,
  };

  await writeJson(`life-log/${dateStr}.json`, log);
  return log;
}

export async function getTodayLog(): Promise<DailyLog> {
  return generateDailyLog();
}

export async function getLogByDate(dateStr: string): Promise<DailyLog | null> {
  return readJson<DailyLog>(`life-log/${dateStr}.json`);
}
