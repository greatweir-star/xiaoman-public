import { callKIMI } from "../llm/kimi-service.js";
import { buildStaticPrefix } from "../prompt/static-prefix.js";
import { buildDynamicSuffix } from "../prompt/dynamic-suffix.js";
import { readJson, writeJson, getUserProfile, updateUserProfile } from "../memory/store.js";
import { compactIfNeeded } from "../compaction.js";
import { nightGuard } from "../hooks/night-guard.js";
import { quqiuInject } from "../hooks/quqiu-inject.js";
import { extractMemories } from "../hooks/memory-extract.js";
import { generateDiary } from "../diary/generator.js";
import { updateProgress, calculateLevel, getLevelName, getLevelProgress, type Progress } from "../progress/calculator.js";
import { queryXiaomanLife, formatLifeContext } from "../life/query.js";

interface WSMessage {
  type: string;
  text?: string;
  userId?: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  emotion?: string;
  timestamp?: number;
}

export async function handleMessage(
  msg: WSMessage,
  sessionMessages: ChatMessage[],
  sendReply: (payload: any) => void
): Promise<void> {
  if (msg.type === "greeting") {
    // 开场白：根据时间生成
    const hour = new Date().getHours();
    let greeting = "嗨，我是小满！";
    if (hour >= 6 && hour < 11) greeting = "早啊...我昨晚没睡好";
    else if (hour >= 11 && hour < 14) greeting = "食堂今天有糖醋排骨但我没抢到";
    else if (hour >= 14 && hour < 18) greeting = "下午好烦啊，数学课我差点睡着";
    else if (hour >= 18 && hour < 22) greeting = "终于下课了！我今天被英语老师点名了";
    else greeting = "这么晚了你还在这？我作业还没写完";

    sendReply({ sender: "xiaoman", text: greeting, emotion: "温柔" });
    return;
  }

  if (msg.type !== "chat" || !msg.text) return;

  const userId = msg.userId || "default";

  // 读取用户信息
  const profile = await getUserProfile(userId);
  const userGender = (profile?.gender as string) || "female";
  const userName = (profile?.name as string) || "还不知道";
  const userGrade = (profile?.grade as string) || "还不知道";

  // 1. 获取上次对话时间（从最后一条有timestamp的消息）
  const lastMsg = sessionMessages.findLast((m) => m.timestamp);
  const lastChatTime = lastMsg?.timestamp;

  // 生成对话摘要（从compaction结果或原始消息）
  const summary = generateQuickSummary(sessionMessages);

  // 2. 查询小满生活状态（增加活人感）
  const lifeContext = await queryXiaomanLife();
  const lifeText = formatLifeContext(lifeContext);

  // 3. 组装 System Prompt
  const staticPrefix = buildStaticPrefix(userGender);
  const dynamicSuffix = buildDynamicSuffix({
    gender: userGender,
    userName,
    grade: userGrade,
    lastChatTime,
    messageCount: sessionMessages.length,
    summary,
  });
  const systemPrompt = `${staticPrefix}\n${dynamicSuffix}${lifeText}`;

  // 2. 上下文压缩
  const compacted = await compactIfNeeded(sessionMessages);

  // 3. 深夜模式检查
  const context = { reply: { text: "" }, stopPropagation: false };
  nightGuard(context);
  if (context.stopPropagation) {
    sendReply({ sender: "xiaoman", text: context.reply.text, emotion: "困倦" });
    return;
  }

  // 4. 调用 KIMI
  const history = compacted.map((m: ChatMessage) => ({
    role: m.role,
    content: m.content,
  }));

  try {
    const result = await callKIMI(systemPrompt, history, msg.text);

    // 5. 蛐蛐注入
    const replyContext = { reply: { text: result.text } };
    quqiuInject(replyContext);

    sendReply({
      sender: "xiaoman",
      text: replyContext.reply.text,
      emotion: result.emotion || "温柔",
    });

    // 6. 猜心情游戏（每6小时最多一次，基于上下文情绪词）
    const lastGuessTime = profile?.lastGuessMoodTime as number || 0;
    const sixHours = 6 * 60 * 60 * 1000;
    if (Date.now() - lastGuessTime > sixHours) {
      const detectedEmotion = detectEmotionFromContext(sessionMessages);
      if (detectedEmotion) {
        setTimeout(() => {
          sendReply({
            sender: "xiaoman",
            text: `等一下，我猜你现在心情是「${detectedEmotion}」，对不对？`,
            emotion: "调皮",
          });
        }, 1000);
        // 更新上次猜心情时间
        await updateUserProfile(userId, "lastGuessMoodTime", String(Date.now()));
      }
    }

    // 7. 提取记忆
    await extractMemories({
      userId,
      sessionMessages: sessionMessages.map((m) => ({
        role: m.role,
        content: m.content,
      })),
    });

    // 7. 更新进度
    const progressData = await readJson<Progress>(`progress/${userId}.json`) || {
      total_dialogue_turns: 0,
      total_usage_days: 0,
      login_streak: 0,
      last_login_date: "",
    };
    const updatedProgress = updateProgress(progressData);
    await writeJson(`progress/${userId}.json`, updatedProgress);

    // 8. 生成日记
    const today = new Date().toISOString().split("T")[0];
    const diaryData = await readJson<{ date: string; content: string }>(`diary/${userId}.json`);
    if (!diaryData || diaryData.date !== today) {
      const dailyState = {
        date: today,
        mood_today: result.emotion || "平静",
        outfit_today: "",
        current_activity: "聊天",
        chat_turn_count: updatedProgress.total_dialogue_turns,
        thoughts_today: [],
      };
      const diaryContent = generateDiary(dailyState, updatedProgress);
      await writeJson(`diary/${userId}.json`, { date: today, content: diaryContent });
    }
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    console.error("LLM call failed:", errorMsg);
    sendReply({
      sender: "xiaoman",
      text: `哎呀，我脑子卡了一下（${errorMsg}），你再说一遍？`,
      emotion: "困惑",
    });
  }
}

/**
 * 快速生成对话摘要，避免"前言不搭后语"
 */
function generateQuickSummary(messages: ChatMessage[]): string {
  if (messages.length === 0) return "这是今天第一次聊天。";

  const lastFew = messages.slice(-6);
  const userMsgs = lastFew.filter((m) => m.role === "user").map((m) => m.content);
  const assistantMsgs = lastFew.filter((m) => m.role === "assistant").map((m) => m.content);

  if (userMsgs.length === 0) return "我们之前聊了几句，但还没说什么具体内容。";

  let summary = "刚才我们在聊：";
  if (userMsgs.length >= 2) {
    summary += `你先说了「${userMsgs[userMsgs.length - 2].slice(0, 20)}...」，然后聊到「${userMsgs[userMsgs.length - 1].slice(0, 20)}...」`;
  } else {
    summary += `你提到了「${userMsgs[0].slice(0, 30)}...」`;
  }

  if (assistantMsgs.length > 0) {
    summary += `，我回复了「${assistantMsgs[assistantMsgs.length - 1].slice(0, 20)}...」`;
  }

  return summary;
}

/**
 * 从用户最近对话中检测情绪关键词
 * 返回检测到的情绪，没有则返回 null
 */
function detectEmotionFromContext(messages: ChatMessage[]): string | null {
  const emotionKeywords: Record<string, string[]> = {
    "累": ["累", "困", "困死了", "好累", "疲惫", "疲倦", " exhaustion"],
    "开心": ["开心", "高兴", "爽", "棒", "快乐", "兴奋", "开心", "耶", "哈哈"],
    "烦": ["烦", "烦死了", "好烦", "烦躁", "烦人", "讨厌", "暴躁"],
    "难过": ["难过", "伤心", "想哭", "不开心", "沮丧", "失落", "郁闷"],
    "焦虑": ["焦虑", "紧张", "压力大", "害怕", "担心", "慌", "愁"],
    "无聊": ["无聊", "没意思", "没劲", "乏味", "枯燥"],
  };

  // 只检查最近3条用户消息
  const recentUserMsgs = messages
    .filter((m) => m.role === "user")
    .slice(-3)
    .map((m) => m.content)
    .join(" ");

  for (const [emotion, keywords] of Object.entries(emotionKeywords)) {
    for (const keyword of keywords) {
      if (recentUserMsgs.includes(keyword)) {
        return emotion;
      }
    }
  }

  return null;
}
