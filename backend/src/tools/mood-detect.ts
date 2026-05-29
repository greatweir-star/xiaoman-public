export function createMoodDetectTool(): any {
  return {
    name: "mood_detect",
    description: "检测用户消息中的情绪关键词",
    parameters: {
      type: "object",
      properties: {
        text: { type: "string", description: "用户消息内容" },
      },
      required: ["text"],
    },
    execute: async (_toolCallId: string, params: { text: string }) => {
      const emotionKeywords: Record<string, string[]> = {
        开心: ["开心", "高兴", "爽", "棒", "耶", "哈哈"],
        难过: ["难过", "伤心", "想哭", "emo", "丧"],
        烦: ["烦", "讨厌", "无语", "烦死了", "暴躁"],
        累: ["累", "困", "疲惫", "想睡", "撑不住"],
        焦虑: ["焦虑", "紧张", "慌", "压力大", "害怕"],
        生气: ["生气", "愤怒", "气死", "火大", "md"],
      };

      for (const [emotion, keywords] of Object.entries(emotionKeywords)) {
        for (const kw of keywords) {
          if (params.text.includes(kw)) {
            return { emotion, confidence: 0.8 };
          }
        }
      }

      return { emotion: "平静", confidence: 0.5 };
    },
  };
}
