/**
 * 小满后端入口
 * 同时支持独立运行（通过 server.ts）和作为模块导入
 */

export { handleMessage } from "./gateway/message-handler.js";
export { callKIMI, callKIMIStream } from "./llm/kimi-service.js";
export { buildStaticPrefix } from "./prompt/static-prefix.js";
export { buildDynamicSuffix } from "./prompt/dynamic-suffix.js";
export { nightGuard } from "./hooks/night-guard.js";
export { quqiuInject } from "./hooks/quqiu-inject.js";
export { extractMemories } from "./hooks/memory-extract.js";
export { compactIfNeeded } from "./compaction.js";
export { updateProgress, calculateLevel, getLevelName, getLevelProgress } from "./progress/calculator.js";
export { generateDiary } from "./diary/generator.js";
