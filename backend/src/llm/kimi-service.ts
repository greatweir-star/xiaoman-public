/**
 * LLM 服务封装
 * 模型配置从 xiaoman.json 读取，支持快速切换 provider/model
 * 支持流式输出（stream）和非流式（blocking）两种模式
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

export interface StreamChunk {
  text: string;
  emotion?: string;
  done: boolean;
}

function buildMessages(systemPrompt: string, history: LLMMessage[], userMessage: string): LLMMessage[] {
  return [
    { role: "system", content: systemPrompt },
    ...history,
    { role: "user", content: userMessage },
  ];
}

function extractEmotion(text: string): { cleanText: string; emotion?: string } {
  const emotionMatch = text.match(/<emotion>(.+?)<\/emotion>/);
  const emotion = emotionMatch ? emotionMatch[1] : undefined;
  const cleanText = text.replace(/<emotion>.+?<\/emotion>/g, "").trim();
  return { cleanText, emotion };
}

// ===== 非流式调用（保留兼容） =====
export async function callKIMI(
  systemPrompt: string,
  history: LLMMessage[],
  userMessage: string
): Promise<LLMResponse> {
  if (!API_KEY) {
    throw new Error(`环境变量 ${modelConfig.apiKeyEnv} 未设置`);
  }

  const messages = buildMessages(systemPrompt, history, userMessage);
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
    const { cleanText, emotion } = extractEmotion(text);

    return { text: cleanText, emotion };
  } catch (err) {
    console.error("[LLM] Fetch error:", err);
    throw err;
  }
}

// ===== 流式调用 =====
export async function* callKIMIStream(
  systemPrompt: string,
  history: LLMMessage[],
  userMessage: string
): AsyncGenerator<StreamChunk, void, unknown> {
  if (!API_KEY) {
    throw new Error(`环境变量 ${modelConfig.apiKeyEnv} 未设置`);
  }

  const messages = buildMessages(systemPrompt, history, userMessage);
  console.log("[LLM Stream] Provider:", modelConfig.provider, "Model:", MODEL);

  const response = await fetch(`${BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${API_KEY}`,
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      model: MODEL,
      messages,
      temperature: TEMPERATURE,
      max_tokens: MAX_TOKENS,
      stream: true,
    }),
  });

  if (!response.ok) {
    const errText = await response.text();
    console.error("[LLM Stream] API error:", response.status, errText);
    throw new Error(`LLM API error: ${response.status} - ${errText}`);
  }

  if (!response.body) {
    throw new Error("LLM API response body is empty");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let fullText = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data:")) continue;

        const dataStr = trimmed.slice(5).trim();
        if (dataStr === "[DONE]") {
          const { cleanText, emotion } = extractEmotion(fullText);
          yield { text: cleanText, emotion, done: true };
          return;
        }

        try {
          const json = JSON.parse(dataStr);
          const delta = json.choices?.[0]?.delta?.content || "";
          if (delta) {
            fullText += delta;
            yield { text: delta, done: false };
          }
        } catch {
          // 忽略解析失败的行
        }
      }
    }

    // 流结束但没有收到 [DONE]
    const { cleanText, emotion } = extractEmotion(fullText);
    yield { text: cleanText, emotion, done: true };
  } finally {
    reader.releaseLock();
  }
}
