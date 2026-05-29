/**
 * 小满后端入口
 * 同时支持独立运行（通过 server.ts）和作为模块导入
 */

export { handleMessage } from "./gateway/message-handler.js";
export { callKIMI } from "./llm/kimi-service.js";
export { buildStaticPrefix } from "./prompt/static-prefix.js";
export { buildDynamicSuffix } from "./prompt/dynamic-suffix.js";
export { bestieAgent } from "./agents/bestie.js";
export { galFriendAgent } from "./agents/gal-friend.js";
export { nightGuard } from "./hooks/night-guard.js";
export { quqiuInject } from "./hooks/quqiu-inject.js";
export { extractMemories } from "./hooks/memory-extract.js";
export { createTimeSenseTool } from "./tools/time-sense.js";
export { createMemoryReadTool } from "./tools/memory-read.js";
export { createMemoryWriteTool } from "./tools/memory-write.js";
export { createMoodDetectTool } from "./tools/mood-detect.js";
export { compactIfNeeded } from "./compaction.js";
export { updateProgress, calculateLevel, getLevelName, getLevelProgress } from "./progress/calculator.js";
export { generateDiary } from "./diary/generator.js";
