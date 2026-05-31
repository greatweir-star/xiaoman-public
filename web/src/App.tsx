import { apiJson, apiPostJson, getAccessToken, getGatewayUrl } from "./lib/backend";
import { useState, useEffect, useRef, useCallback } from "react";
import OnboardingFlow, { type OnboardingConfig } from "./components/OnboardingFlow";
import ChatPage, { type ChatMessage } from "./pages/ChatPage";
import LifePage from "./pages/LifePage";
import SettingsPage from "./pages/SettingsPage";
import DiaryPage from "./pages/DiaryPage";
import MemoryPage from "./pages/MemoryPage";
import GrowthPage from "./pages/GrowthPage";
import ReportPage from "./pages/ReportPage";
import WorldDetailPage from "./pages/WorldDetailPage";
import AvatarLightbox from "./components/AvatarLightbox";
import { useDailyAvatar } from "./hooks/useDailyAvatar";
import { getTodayAvatarKey } from "./components/DailyAvatar";
import {
  resolveCompanionPortraitUrl,
  type CompanionStyle,
} from "./lib/companionAvatar";

const GATEWAY_URL = getGatewayUrl();

interface XiaomanConfig {
  name: string;
  gender: "female" | "male";
  style: string;
  grade: number;
}

type View = "chat" | "life" | "settings" | "diary" | "memory" | "growth" | "report" | "xiaoman-world" | "user-world";

export default function App() {
  const [onboarded, setOnboarded] = useState(() =>
    localStorage.getItem("xiaoman_onboarded") === "true"
  );
  const [config, setConfig] = useState<XiaomanConfig>(() => ({
    name: localStorage.getItem("xiaoman_name") || "小满",
    gender: (localStorage.getItem("xiaoman_gender") || "female") as "female" | "male",
    style: localStorage.getItem("xiaoman_style") || "fresh",
    grade: Number(localStorage.getItem("xiaoman_grade") || "8"),
  }));
  const [view, setView] = useState<View>("chat");
  const [currentEmotion, setCurrentEmotion] = useState("温柔");
  const [xiaomanStatus, setXiaomanStatus] = useState({ activity: "", energy: 50 });
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [chatToast, setChatToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [userId] = useState(() => {
    let id = localStorage.getItem("xiaoman_user_id");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("xiaoman_user_id", id);
    }
    return id;
  });

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const connecting = useRef(false);
  const mounted = useRef(true);

  const [isSleeping, setIsSleeping] = useState(() => {
    const h = new Date().getHours();
    return h >= 23 || h < 6;
  });
  const [skillTree, setSkillTree] = useState({
    level: 1,
    name: "新同桌",
    xp: 0,
    next_threshold: 20,
  });
  const [companionCode, setCompanionCode] = useState("");
  const [todayStatus, setTodayStatus] = useState("");
  const dailyAvatar = useDailyAvatar(userId, config.style);
  const portraitUrl = resolveCompanionPortraitUrl(config.style, dailyAvatar?.url);
  const [avatarLightbox, setAvatarLightbox] = useState(false);

  const fetchSkillTree = useCallback(async () => {
    const data = await apiJson<any | null>(`/api/world/${userId}/skill-tree`, null);
    if (!data) return;
    setSkillTree({
      level: data.level ?? 1,
      name: data.name ?? "\u65b0\u540c\u684c",
      xp: data.xp ?? 0,
      next_threshold: data.next_threshold ?? 20,
    });
  }, [userId]);
  const handleStyleChange = useCallback((style: CompanionStyle) => {
    setConfig((prev) => {
      const next = { ...prev, style };
      localStorage.setItem("xiaoman_style", style);
      return next;
    });
  }, []);

  const syncIdentityToBackend = useCallback(async (cfg: XiaomanConfig) => {
    await apiPostJson(`/api/world/${userId}/identity`, {
      companion_name: cfg.name,
      xiaoman_name: cfg.name,
      grade: cfg.grade,
      gender: cfg.gender,
      style: cfg.style,
    }, null);
  }, [userId]);

  // 获取小满状态
  const fetchXiaomanStatus = useCallback(async () => {
    const data = await apiJson<any | null>(`/api/world/${userId}/xiaoman`, null);
    if (!data) return;
    setXiaomanStatus({
      activity: data.schedule?.current_activity || "",
      energy: data.emotion?.energy || 50,
    });
    if (data.emotion?.current_emotion) {
      setCurrentEmotion(data.emotion.current_emotion);
    }
    if (data.companion_code) {
      setCompanionCode(data.companion_code);
    }
    const today = data.schedule?.xiaoman_today;
    if (today?.mood) {
      setTodayStatus(today.mood);
    }
  }, [userId]);
  useEffect(() => {
    if (!onboarded) return;
    fetchXiaomanStatus();
    fetchSkillTree();
    const timer = setInterval(fetchXiaomanStatus, 30000);
    return () => clearInterval(timer);
  }, [onboarded, fetchXiaomanStatus, fetchSkillTree]);

  // WebSocket 连接（全局管理，供 ChatPage 使用）
  const showToast = useCallback((text: string) => {
    setChatToast(text);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setChatToast(null), 4000);
  }, []);

  const connectWs = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;
    if (connecting.current) return;
    connecting.current = true;
    try {
      const socket = new WebSocket(GATEWAY_URL);
      ws.current = socket;
      socket.onopen = () => {
        connecting.current = false;
        setConnected(true);
        const accessToken = getAccessToken();
        socket.send(JSON.stringify({ type: "auth", userId, ...(accessToken ? { accessToken } : {}) }));
        if (heartbeatTimer.current) clearInterval(heartbeatTimer.current);
        heartbeatTimer.current = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
          }
        }, 30000);
        // 每日形象变化问候
        const todayKey = getTodayAvatarKey(userId);
        const lastKey = localStorage.getItem("xiaoman_last_avatar_key");
        const lastGreetDate = localStorage.getItem("xiaoman_avatar_greet_date");
        const todayStr = new Date().toISOString().slice(0, 10);
        if (lastKey && lastKey !== todayKey && lastGreetDate !== todayStr) {
          setMessages((prev) => [
            ...prev,
            {
              sender: "xiaoman",
              text: "今天换了一套衣服，你觉得怎么样？",
              kind: "normal",
              timestamp: Date.now(),
            },
          ]);
          localStorage.setItem("xiaoman_avatar_greet_date", todayStr);
        }
        localStorage.setItem("xiaoman_last_avatar_key", todayKey);
      };
      socket.onclose = () => {
        setConnected(false);
        ws.current = null;
        connecting.current = false;
        if (heartbeatTimer.current) {
          clearInterval(heartbeatTimer.current);
          heartbeatTimer.current = null;
        }
        if (mounted.current) {
          reconnectTimer.current = setTimeout(() => connectWs(), 3000);
        }
      };
      socket.onerror = () => {
        connecting.current = false;
        setConnected(false);
      };
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "pong") {
            return;
          }

          if (data.type === "error") {
            showToast(data.payload?.message || "发送失败");
            setIsTyping(false);
            return;
          }

          if (data.type === "auth_error") {
            showToast(data.payload?.detail || "登录状态已失效");
            setIsTyping(false);
            return;
          }

          if (data.type === "typing") {
            setIsTyping(!!data.payload?.active);
            return;
          }

          if (data.type === "memory_recall" && data.payload?.items?.length) {
            const texts = data.payload.items
              .map((it: { text?: string }) => it.text)
              .filter(Boolean);
            if (texts.length) {
              setMessages((prev) => [
                ...prev,
                {
                  sender: "system",
                  kind: "memory_recall",
                  text: texts.join("；"),
                  memories: texts,
                  timestamp: Date.now(),
                },
              ]);
            }
            return;
          }

          if (data.type === "linkage_triggered" && data.payload?.changes?.length) {
            const label = data.payload.changes
              .map((c: { linkage?: string; result?: string }) => c.result || c.linkage)
              .filter(Boolean)
              .join(" · ");
            if (label) showToast(label);
            return;
          }

          if (data.type === "skill_unlocked") {
            const msg =
              data.payload?.message ||
              `关系升级 L${data.payload?.old_level} → L${data.payload?.new_level}`;
            showToast(msg);
            void fetchSkillTree();
            return;
          }

          if (data.type === "rest_reminder") {
            showToast(data.payload?.message || "休息一下眼睛吧～");
            return;
          }

          if (data.type === "stream_start" && data.payload?.messageId) {
            setIsTyping(false);
            setMessages((prev) => [
              ...prev,
              {
                sender: "xiaoman",
                text: "",
                kind: "normal",
                streamMessageId: data.payload.messageId,
                streaming: true,
                timestamp: Date.now(),
              },
            ]);
            return;
          }

          if (data.type === "stream_delta" && data.payload?.messageId) {
            const { messageId, delta } = data.payload;
            if (!delta) return;
            setMessages((prev) =>
              prev.map((m) =>
                m.streamMessageId === messageId
                  ? { ...m, text: m.text + delta }
                  : m
              )
            );
            return;
          }

          if (data.type === "stream_end" && data.payload?.messageId) {
            const p = data.payload;
            setMessages((prev) =>
              prev.map((m) =>
                m.streamMessageId === p.messageId
                  ? {
                      ...m,
                      text: p.text ?? m.text,
                      emotion: p.emotion,
                      streaming: false,
                      streamMessageId: undefined,
                    }
                  : m
              )
            );
            if (p.emotion) setCurrentEmotion(p.emotion);
            if (typeof p.isSleeping === "boolean") setIsSleeping(p.isSleeping);
            if (typeof p.energy === "number") {
              setXiaomanStatus((prev) => ({ ...prev, energy: p.energy }));
            }
            setIsTyping(false);
            return;
          }

          if (data.type === "message" && data.payload?.emotion) {
            setCurrentEmotion(data.payload.emotion);
          }
          if (data.type === "message" && typeof data.payload?.isSleeping === "boolean") {
            setIsSleeping(data.payload.isSleeping);
          }
          if (data.type === "message" && data.payload?.companionCode) {
            setCompanionCode(data.payload.companionCode);
          }
          if (data.type === "message" && data.payload?.todayStatus) {
            setTodayStatus(data.payload.todayStatus);
          }
          if (data.type === "message") {
            setMessages((prev) => [
              ...prev,
              { ...data.payload, kind: "normal", timestamp: Date.now() },
            ]);
            setIsTyping(false);
          }
        } catch {
          // ignore
        }
      };
    } catch {
      connecting.current = false;
      setConnected(false);
    }
  }, [userId, showToast, fetchSkillTree]);

  useEffect(() => {
    mounted.current = true;
    if (!onboarded) return;
    connectWs();
    return () => {
      mounted.current = false;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      if (heartbeatTimer.current) {
        clearInterval(heartbeatTimer.current);
        heartbeatTimer.current = null;
      }
      ws.current?.close();
    };
  }, [onboarded, connectWs]);

  const handleOnboardingDone = (cfg: OnboardingConfig) => {
    setConfig(cfg);
    setOnboarded(true);
    void syncIdentityToBackend(cfg);
  };

  const navigate = (v: View) => {
    (document.activeElement as HTMLElement)?.blur();
    setView(v);
  };
  const goBack = () =>
    setView(view === "diary" || view === "memory" || view === "growth" || view === "report" ? "life" : "settings");

  const sendMessage = useCallback((text: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      setMessages((prev) => [...prev, { sender: "user", text, timestamp: Date.now() }]);
      ws.current.send(JSON.stringify({ type: "chat", text, userId }));
      setIsTyping(true);
    }
  }, [userId, ws]);

  if (!onboarded) {
    return <OnboardingFlow onDone={handleOnboardingDone} />;
  }

  // 底部 Tab 始终显示，一级/二级/三级菜单都固定
  const showTabBar = true;

  return (
    <div className={`chat-interface${isSleeping ? " night-mode" : ""}`}>
      {/* 页面内容 */}
      <div className="page-container">
        {view === "chat" && (
          <ChatPage
            config={config}
            messages={messages}
            isTyping={isTyping}
            onSendMessage={sendMessage}
            connected={connected}
            currentEmotion={currentEmotion}
            xiaomanStatus={xiaomanStatus}
            toast={chatToast}
            isSleeping={isSleeping}
            skillTree={skillTree}
            dailyAvatarUrl={portraitUrl}
            dailyAvatarLabel={dailyAvatar?.label}
            companionCode={companionCode}
            todayStatus={todayStatus}
            onAvatarClick={() => setAvatarLightbox(true)}
            userId={userId}
          />
        )}
        {view === "life" && (
          <LifePage
            userId={userId}
            config={config}
            currentEmotion={currentEmotion}
            onNavigate={(v) => navigate(v)}
            dailyAvatarUrl={portraitUrl}
            dailyAvatarLabel={dailyAvatar?.label}
            onAvatarClick={() => setAvatarLightbox(true)}
          />
        )}
        {view === "settings" && (
          <SettingsPage
            userId={userId}
            style={config.style}
            onStyleChange={handleStyleChange}
            onNavigate={navigate}
          />
        )}
        {view === "diary" && <DiaryPage userId={userId} onBack={goBack} />}
        {view === "memory" && <MemoryPage userId={userId} onBack={goBack} />}
        {view === "growth" && <GrowthPage userId={userId} onBack={goBack} onNavigate={() => navigate("report")} />}
        {view === "report" && <ReportPage userId={userId} onBack={goBack} />}
        {view === "xiaoman-world" && <WorldDetailPage userId={userId} side="xiaoman" onBack={goBack} />}
        {view === "user-world" && <WorldDetailPage userId={userId} side="user" onBack={goBack} />}
      </div>

      {/* 底部常驻 Tab — 所有页面固定显示 */}
      {avatarLightbox && (
        <AvatarLightbox
          src={portraitUrl}
          label={dailyAvatar?.label ? `今日 · ${dailyAvatar.label}` : undefined}
          onClose={() => setAvatarLightbox(false)}
        />
      )}

      {showTabBar && (
        <div className="tab-bar">
          <button
            className={`tab-item ${view === "chat" ? "active" : ""}`}
            onClick={() => setView("chat")}
          >
            <svg className="tab-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span className="tab-label">聊天</span>
          </button>
          <button
            className={`tab-item ${view === "life" ? "active" : ""}`}
            onClick={() => setView("life")}
          >
            <svg className="tab-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
            </svg>
            <span className="tab-label">life</span>
          </button>
          <button
            className={`tab-item ${view === "settings" ? "active" : ""}`}
            onClick={() => setView("settings")}
          >
            <svg className="tab-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 0 0 2.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 0 0 1.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 0 0-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 0 0-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 0 0-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 0 0-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 0 0 1.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path d="M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0" />
            </svg>
            <span className="tab-label">设置</span>
          </button>
        </div>
      )}
    </div>
  );
}
