import { updateMemory } from "../memory/store.js";

interface Message {
  role: string;
  content: string;
}

interface Context {
  userId: string;
  sessionMessages: Message[];
}

export async function extractMemories(context: Context): Promise<void> {
  const messages = context.sessionMessages;
  const lastUserMessage = messages.findLast((m: Message) => m.role === "user");

  if (!lastUserMessage) return;

  const text = lastUserMessage.content;

  // 规则提取：名字
  const nameMatch = text.match(/叫我(.+?)[吧|嘛|呢]/);
  if (nameMatch) {
    await updateMemory(context.userId, "identity", "name", nameMatch[1].trim());
  }

  // 规则提取：情绪关键词
  const emotionKeywords = ["开心", "难过", "烦", "累", "焦虑", "生气"];
  for (const kw of emotionKeywords) {
    if (text.includes(kw)) {
      await updateMemory(context.userId, "workflow", "last_emotion", kw);
    }
  }

  // 规则提取：年级
  const gradeMatch = text.match(/(初一|初二|初三|高一|高二|高三)/);
  if (gradeMatch) {
    await updateMemory(context.userId, "identity", "grade", gradeMatch[1]);
  }
}
