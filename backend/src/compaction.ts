/**
 * Compaction: 上下文压缩
 * 当对话历史超过阈值时，自动压缩为摘要，保留关键信息
 */

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp?: number;
}

const MAX_MESSAGES = 12; // 超过12条触发压缩
const KEEP_RECENT = 4;   // 保留最近4条不压缩

export async function compactIfNeeded(messages: Message[]): Promise<Message[]> {
  if (messages.length <= MAX_MESSAGES) {
    return messages;
  }

  const toCompress = messages.slice(0, messages.length - KEEP_RECENT);
  const recent = messages.slice(messages.length - KEEP_RECENT);

  // MVP阶段用规则压缩，不用LLM（节省token和复杂度）
  const summary = generateSummary(toCompress);

  const compacted: Message = {
    role: "assistant",
    content: `[历史对话摘要] ${summary}`,
    timestamp: Date.now(),
  };

  return [compacted, ...recent];
}

function generateSummary(messages: Message[]): string {
  const userMessages = messages.filter((m) => m.role === "user").map((m) => m.content);
  const topics = extractTopics(userMessages);

  if (topics.length === 0) {
    return "聊了一些日常";
  }

  return `主要聊到了：${topics.join("、")}`;
}

function extractTopics(messages: string[]): string[] {
  const keywords = [
    "作业", "考试", "数学", "英语", "物理", "化学",
    "食堂", "早餐", "午餐", "晚餐",
    "老师", "同学", "朋友", "同桌",
    "游戏", "王者", "蛋仔",
    "小说", "漫画", "番剧",
    "开心", "难过", "烦", "累", "焦虑",
  ];

  const found = new Set<string>();
  for (const msg of messages) {
    for (const kw of keywords) {
      if (msg.includes(kw)) {
        found.add(kw);
      }
    }
  }

  return Array.from(found).slice(0, 5);
}
