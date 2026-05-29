export function createTimeSenseTool(): any {
  return {
    name: "time_sense",
    description: "获取当前时间，决定小满的开场白和状态",
    parameters: {
      type: "object",
      properties: {},
    },
    execute: async () => {
      const now = new Date();
      const hour = now.getHours();
      let greeting: string;
      let mood: string;

      if (hour >= 6 && hour < 11) {
        greeting = "早啊...我昨晚没睡好，一直在想那道物理题";
        mood = "困";
      } else if (hour >= 11 && hour < 14) {
        greeting = "食堂今天有糖醋排骨但我没抢到，你在干嘛？";
        mood = "懒";
      } else if (hour >= 14 && hour < 18) {
        greeting = "下午好烦啊，数学课我差点睡着";
        mood = "烦";
      } else if (hour >= 18 && hour < 22) {
        greeting = "终于下课了！我今天被英语老师点名了，救命";
        mood = "开心";
      } else {
        greeting = "这么晚了你还在这？我作业还没写完";
        mood = "焦虑";
      }

      return { time: now.toISOString(), hour, greeting, mood };
    },
  };
}
