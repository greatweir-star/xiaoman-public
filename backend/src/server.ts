import { createServer } from "http";
import express from "express";
import cors from "cors";
import { WebSocketServer } from "ws";
import { handleMessage } from "./gateway/message-handler.js";
import { readJson, writeJson, getUserProfile, updateUserProfile } from "./memory/store.js";
import { calculateLevel, getLevelName, getLevelProgress, type Progress } from "./progress/calculator.js";
import { queryXiaomanLife } from "./life/query.js";

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

// ===== Express HTTP 服务器 =====
const app = express();
app.use(cors());
app.use(express.json());

// 健康检查
app.get("/health", (_req, res) => {
  res.json({ status: "ok", time: new Date().toISOString() });
});

// POST /api/world/:userId/identity — 保存用户身份
app.post("/api/world/:userId/identity", async (req, res) => {
  const { userId } = req.params;
  const body = req.body || {};
  try {
    if (body.companion_name) await updateUserProfile(userId, "companion_name", String(body.companion_name));
    if (body.xiaoman_name) await updateUserProfile(userId, "xiaoman_name", String(body.xiaoman_name));
    if (body.grade) await updateUserProfile(userId, "grade", String(body.grade));
    if (body.gender) await updateUserProfile(userId, "gender", String(body.gender));
    if (body.style) await updateUserProfile(userId, "style", String(body.style));
    res.json({ success: true, userId });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    res.status(500).json({ success: false, error: msg });
  }
});

// GET /api/world/:userId/skill-tree — 获取能力树
app.get("/api/world/:userId/skill-tree", async (req, res) => {
  const { userId } = req.params;
  try {
    const progress = await readJson<Progress>(`progress/${userId}.json`) || {
      total_dialogue_turns: 0,
      total_usage_days: 0,
      login_streak: 0,
      last_login_date: "",
    };
    const level = calculateLevel(progress);
    const name = getLevelName(level);
    const xp = getLevelProgress(progress);
    res.json({
      level,
      name,
      xp: xp.current,
      next_threshold: xp.total,
      total_turns: progress.total_dialogue_turns,
      total_days: progress.total_usage_days,
      login_streak: progress.login_streak,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    res.status(500).json({ success: false, error: msg });
  }
});

// GET /api/world/:userId/xiaoman — 获取小满状态
app.get("/api/world/:userId/xiaoman", async (_req, res) => {
  try {
    const life = await queryXiaomanLife();
    res.json({
      schedule: {
        current_activity: life.activity,
        period: life.periodName,
        xiaoman_today: {
          mood: life.currentMood,
          breakfast: life.todayLog.breakfast,
          lunch: life.todayLog.lunch,
          dinner: life.todayLog.dinner,
        },
      },
      emotion: {
        current_emotion: life.currentMood,
        energy: life.energy,
      },
      companion_code: "XM-" + Math.random().toString(36).slice(2, 6).toUpperCase(),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    res.status(500).json({ success: false, error: msg });
  }
});

// ===== WebSocket 服务器（共享同一个 HTTP 服务器）=====
const server = createServer(app);
const wss = new WebSocketServer({ server });

wss.on("connection", (ws) => {
  let sessionId = Math.random().toString(36).slice(2);

  ws.on("message", async (data) => {
    try {
      const msg = JSON.parse(data.toString());

      // 心跳
      if (msg.type === "ping") {
        ws.send(JSON.stringify({ type: "pong" }));
        return;
      }

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

      await handleMessage(
        { ...msg, userId: sessionId },
        sessionMessages,
        (payload) => {
          ws.send(JSON.stringify({ type: "message", payload }));
          if (payload.sender === "xiaoman") {
            sessionMessages.push({
              role: "assistant",
              content: payload.text,
              emotion: payload.emotion,
            });
          }
        },
        (data) => {
          ws.send(JSON.stringify(data));
        }
      );

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

server.listen(PORT, () => {
  console.log(`Xiaoman server running on http://localhost:${PORT} / ws://localhost:${PORT}`);
});
