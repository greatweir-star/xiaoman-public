import { WebSocketServer } from "ws";
import { handleMessage } from "./gateway/message-handler.js";
import { readJson, writeJson } from "./memory/store.js";

const PORT = parseInt(process.env.PORT || "18789");
const SESSION_DIR = "sessions";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  emotion?: string;
  timestamp?: number;
}

const sessions = new Map<string, ChatMessage[]>();

async function loadSession(sessionId: string): Promise<ChatMessage[]> {
  const data = await readJson<ChatMessage[]>(`${SESSION_DIR}/${sessionId}.json`);
  return data || [];
}

async function saveSession(sessionId: string, messages: ChatMessage[]): Promise<void> {
  await writeJson(`${SESSION_DIR}/${sessionId}.json`, messages);
}

const wss = new WebSocketServer({ port: PORT });

wss.on("connection", (ws) => {
  let sessionId = Math.random().toString(36).slice(2);

  ws.on("message", async (data) => {
    try {
      const msg = JSON.parse(data.toString());

      // 认证：前端发送固定 userId
      if (msg.type === "auth" && msg.userId) {
        sessionId = msg.userId;
        const loaded = await loadSession(sessionId);
        sessions.set(sessionId, loaded);
        ws.send(JSON.stringify({ type: "auth_ok", userId: sessionId }));
        return;
      }

      const sessionMessages = sessions.get(sessionId) || [];

      if (msg.type === "chat" && msg.text) {
        sessionMessages.push({ role: "user", content: msg.text, timestamp: Date.now() });
      }

      await handleMessage({ ...msg, userId: sessionId }, sessionMessages, (payload) => {
        ws.send(JSON.stringify({ type: "message", payload }));
        if (payload.sender === "xiaoman") {
          sessionMessages.push({
            role: "assistant",
            content: payload.text,
            emotion: payload.emotion,
          });
        }
      });

      // 持久化会话
      await saveSession(sessionId, sessionMessages);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      console.error("Message handling error:", err);
      ws.send(
        JSON.stringify({
          type: "message",
          payload: { sender: "xiaoman", text: `我这边出错了: ${errorMsg}`, emotion: "困惑" },
        })
      );
    }
  });

  ws.on("close", () => {
    sessions.delete(sessionId);
  });
});

console.log(`Xiaoman server running on ws://localhost:${PORT}`);
