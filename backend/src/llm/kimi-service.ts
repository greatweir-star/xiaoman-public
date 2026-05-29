/**
 * LLM 服务封装
 * 模型配置从 xiaoman.json 读取，支持快速切换 provider/model
 */

import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 读取 xiaoman.json 配置
const configPath = join(__dirname, "../../xiaoman.json");
const config = JSON.parse(readFileSync(configPath, "utf-8"));
const modelConfig = config.model;

const BASE_URL = modelConfig.baseUrl;
const MODEL = modelConfig.modelId;
const API_KEY = process.env[modelConfig.apiKeyEnv] || modelConfig.apiKey || "";
const TEMPERATURE = modelConfig.temperature;
const MAX_TOKENS = modelConfig.maxTokens;

interface LLMMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface LLMResponse {
  text: string;
  emotion?: string;
}

export async function callKIMI(
  systemPrompt: string,
  history: LLMMessage[],
  userMessage: string
): Promise<LLMResponse> {
  if (!API_KEY) {
    throw new Error(`环境变量 ${modelConfig.apiKeyEnv} 未设置`);
  }

  const messages: LLMMessage[] = [
    { role: "system", content: systemPrompt },
    ...history,
    { role: "user", content: userMessage },
  ];

  console.log("[LLM] Provider:", modelConfig.provider, "Model:", MODEL);

  try {
    const response = await fetch(`${BASE_URL}/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${API_KEY}`,
      },
      body: JSON.stringify({
        model: MODEL,
        messages,
        temperature: TEMPERATURE,
        max_tokens: MAX_TOKENS,
      }),
    });

    console.log("[LLM] Response status:", response.status);

    if (!response.ok) {
      const errText = await response.text();
      console.error("[LLM] API error:", response.status, errText);
      throw new Error(`LLM API error: ${response.status} - ${errText}`);
    }

    const data = await response.json();
    const text = data.choices?.[0]?.message?.content || "";

    // 从回复中提取 emotion（如果有 <emotion>标签）
    const emotionMatch = text.match(/<emotion>(.+?)<\/emotion>/);
    const emotion = emotionMatch ? emotionMatch[1] : undefined;
    const cleanText = text.replace(/<emotion>.+?<\/emotion>/g, "").trim();

    return { text: cleanText, emotion };
  } catch (err) {
    console.error("[LLM] Fetch error:", err);
    throw err;
  }
}
