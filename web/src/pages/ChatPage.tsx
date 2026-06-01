import { apiJson } from "../lib/backend";
import { useState, useEffect, useRef } from "react";
import XiaomanAvatar from "../components/XiaomanAvatar";
import TypingIndicator from "../components/TypingIndicator";

export interface ChatMessage {
  sender: "xiaoman" | "user" | "system";
  text: string;
  kind?: "memory_recall" | "normal";
  memories?: string[];
  emotion?: string;
  timestamp?: number;
  streamMessageId?: string;
  streaming?: boolean;
  crisis?: boolean;
  resources?: { name: string; phone: string }[];
}

const FUN_PROMPTS = [
  { label: "就想吐槽一下", text: "我现在就想吐槽一下，你先听我说说。" },
  { label: "帮我理一理", text: "我有点乱，可以陪我一起理一理吗？" },
  { label: "先陪我待会儿", text: "先不用解决问题，陪我待会儿就好。" },
] as const;

const SAVE_NUDGE_DISMISSED_AT_KEY = "xiaoman_save_nudge_dismissed_at";
const SAVE_NUDGE_COOLDOWN = 24 * 60 * 60 * 1000;

function containsNegativeKeyword(text: string): boolean {
  const keywords = ["崩溃", "绝望", "痛苦", "想死", "累", "烦", "焦虑", "无聊", "难过", "委屈", "丧"];
  return keywords.some((k) => text.includes(k));
}

function emotionToBubbleColor(emotion: string | undefined): string {
  if (!emotion) return "#F5F5F5";
  if (["崩溃", "绝望", "痛苦", "想死"].some((k) => emotion.includes(k))) return "#7BA7BC";
  if (["累", "烦", "焦虑", "无聊", "难过", "委屈", "丧"].some((k) => emotion.includes(k))) return "#A8C8D8";
  if (["开心", "兴奋", "激动", "幸福"].some((k) => emotion.includes(k))) return "#F5D0A8";
  if (["平静", "温柔", "安心", "放松"].some((k) => emotion.includes(k))) return "#F5E6C8";
  return "#F5F5F5";
}

function formatTime(ts: number | undefined): string {
  if (!ts) return "";
  const d = new Date(ts);
  const h = d.getHours().toString().padStart(2, "0");
  const m = d.getMinutes().toString().padStart(2, "0");
  return `${h}:${m}`;
}

interface UsageStats {
  daily_used: number;
  daily_remaining: number;
  session_used: number;
  session_remaining: number;
  night_locked: boolean;
}

interface ChatPageProps {
  config: { name: string; gender: "female" | "male"; style: string };
  messages: ChatMessage[];
  isTyping: boolean;
  onSendMessage: (text: string) => void;
  connected: boolean;
  currentEmotion: string;
  xiaomanStatus: { activity: string; energy: number };
  toast?: string | null;
  isSleeping?: boolean;
  skillTree?: { level: number; name: string; xp: number; next_threshold: number };
  dailyAvatarUrl?: string;
  dailyAvatarLabel?: string;
  companionCode?: string;
  todayStatus?: string;
  onAvatarClick?: () => void;
  userId?: string;
  authEmail?: string;
  onSaveRelationship?: () => void;
}

export default function ChatPage({
  config,
  messages,
  isTyping,
  onSendMessage,
  connected,
  currentEmotion,
  xiaomanStatus,
  toast,
  isSleeping = false,
  skillTree,
  dailyAvatarUrl,
  dailyAvatarLabel,
  todayStatus,
  onAvatarClick,
  userId,
  authEmail = "",
  onSaveRelationship,
}: ChatPageProps) {
  const [input, setInput] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [inputBreathing, setInputBreathing] = useState(false);
  const [expandedRecalls, setExpandedRecalls] = useState<Set<number>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [sessionWarnDismissed, setSessionWarnDismissed] = useState(false);
  const [saveNudgeDismissed, setSaveNudgeDismissed] = useState(() => {
    const dismissedAt = Number(localStorage.getItem(SAVE_NUDGE_DISMISSED_AT_KEY) || 0);
    return Date.now() - dismissedAt < SAVE_NUDGE_COOLDOWN;
  });

  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    messagesEndRef.current?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
  }, [messages, isTyping, toast]);

  useEffect(() => {
    if (!containsNegativeKeyword(input)) {
      setInputBreathing(false);
      return;
    }
    setInputBreathing(true);
    const timer = setTimeout(() => setInputBreathing(false), 3000);
    return () => clearTimeout(timer);
  }, [input]);

  // 拉取 usage 数据，每 5 分钟刷新
  useEffect(() => {
    if (!userId) return;
    const fetchUsage = async () => {
      const data = await apiJson<UsageStats | null>(`/api/world/${userId}/usage`, null);
      if (data) setUsage(data);
    };
    fetchUsage();
    const timer = setInterval(fetchUsage, 5 * 60 * 1000);
    return () => clearInterval(timer);
  }, [userId]);

  const send = () => {
    if (!input.trim()) return;
    if (!connected) {
      setConnectionError("连接已断开，正在重连…");
      return;
    }
    onSendMessage(input);
    setInput("");
    setConnectionError("");
  };

  const isNightLocked = usage?.night_locked ?? false;
  const isDailyExhausted = usage !== null && usage.daily_remaining <= 0;
  const showSessionWarn =
    !sessionWarnDismissed && usage !== null && usage.session_remaining <= 5 && usage.session_remaining > 0;
  const inputDisabled = !connected || isNightLocked || isDailyExhausted;
  const showSaveNudge =
    !authEmail && !saveNudgeDismissed && messages.filter((message) => message.sender !== "system").length >= 3;

  const dismissSaveNudge = () => {
    localStorage.setItem(SAVE_NUDGE_DISMISSED_AT_KEY, String(Date.now()));
    setSaveNudgeDismissed(true);
  };

  return (
    <div className="chat-page">
      <header className="chat-header-card">
        <div className="chat-header-main">
          <div className="chat-top-left">
            <XiaomanAvatar
              size="sm"
              style={config.style}
              sleeping={isSleeping}
              srcOverride={dailyAvatarUrl}
              enlargeable
              title={dailyAvatarLabel ? `今日 · ${dailyAvatarLabel}` : undefined}
              onClick={onAvatarClick}
            />
            <div className="chat-top-info">
              <span className="chat-top-name">{config.name}</span>
              <span className="chat-top-status">
                {isSleeping ? "睡了" : connected ? "在线" : "连接中…"}
                {!isSleeping && (todayStatus || xiaomanStatus.activity)
                  ? ` · ${todayStatus || xiaomanStatus.activity}`
                  : ""}
              </span>
            </div>
          </div>
          <button
            type="button"
            className="relationship-pill"
            onClick={onSaveRelationship}
            aria-label="查看关系保存状态"
          >
            <span aria-hidden="true">♡</span>
            <span>关系 Lv.{skillTree?.level ?? 1}</span>
          </button>
        </div>
      </header>

      {toast && <div className="chat-toast">{toast}</div>}
      {connectionError && <div className="connection-error">{connectionError}</div>}
      {showSessionWarn && (
        <div className="session-warn-bar">
          已连续使用 {usage?.session_used} 分钟，注意休息一下哦
          <button type="button" onClick={() => setSessionWarnDismissed(true)}>知道了</button>
        </div>
      )}

      <div className="messages">
        {messages.length === 0 && (
          <div className="chat-empty-state">
            <p className="soft-eyebrow">YOUR NEW DESKMATE</p>
            <h2>今天过得怎么样？</h2>
            <p>不用想好再开口。开心的、烦的、没头没尾的，都可以先告诉小满。</p>
          </div>
        )}
        {messages.map((msg, i) => {
          if (msg.sender === "system" && msg.kind === "memory_recall") {
            const texts = msg.memories?.length
              ? msg.memories
              : msg.text.split("；").filter(Boolean);
            return (
              <div key={i} className="memory-recall-banner">
                <span className="memory-recall-label">小满想起了</span>
                <span className="memory-recall-text">{texts.join(" · ")}</span>
              </div>
            );
          }

          const isExpanded = expandedRecalls.has(i);
          return (
            <div key={i} className={`message ${msg.sender}${msg.crisis ? " crisis" : ""}`}>
              {msg.sender === "xiaoman" && (
                <XiaomanAvatar
                  emotion={msg.emotion || currentEmotion}
                  style={config.style}
                  mode="emotion"
                  size="xs"
                />
              )}
              <div className="message-content">
                {msg.sender === "xiaoman" && msg.kind === "memory_recall" && (
                  <button
                    type="button"
                    className="memory-recall-hint"
                    onClick={() => {
                      setExpandedRecalls((prev) => {
                        const next = new Set(prev);
                        if (next.has(i)) next.delete(i);
                        else next.add(i);
                        return next;
                      });
                    }}
                  >
                    「小满想起了你上次说的…」
                    {isExpanded && (
                      <span className="memory-recall-hint-detail">
                        {msg.memories?.length ? msg.memories.join(" · ") : msg.text}
                      </span>
                    )}
                  </button>
                )}
                <div
                  className={`bubble${msg.crisis ? " crisis-bubble" : ""}`}
                  style={
                    msg.sender === "xiaoman" && !msg.crisis
                      ? {
                          backgroundColor: emotionToBubbleColor(msg.emotion || currentEmotion),
                          transition: "background-color 300ms ease",
                        }
                      : undefined
                  }
                >
                  {msg.text.split("\n").map((line, j) => (
                    <p key={j} className={line.startsWith("~>") ? "quqiu" : ""}>{line}</p>
                  ))}
                </div>
                {msg.crisis && msg.resources && msg.resources.length > 0 && (
                  <ul className="crisis-resources">
                    {msg.resources.map((r) => (
                      <li key={r.phone}>
                        <strong>{r.name}</strong> {r.phone}
                      </li>
                    ))}
                  </ul>
                )}
                {msg.timestamp && (
                  <span className="message-timestamp">{formatTime(msg.timestamp)}</span>
                )}
              </div>
            </div>
          );
        })}
        {isTyping && (
          <div className="message xiaoman">
            <XiaomanAvatar style={config.style} mode="emotion" emotion={currentEmotion} size="xs" />
            <div className="bubble"><TypingIndicator /></div>
          </div>
        )}
        {showSaveNudge && (
          <article className="save-relationship-nudge">
            <span className="save-nudge-icon" aria-hidden="true">存</span>
            <div>
              <h3>保存你和小满的进度</h3>
              <p>换个设备回来，她也会记得刚才的事。</p>
              <div className="save-nudge-actions">
                <button type="button" onClick={onSaveRelationship}>保存关系</button>
                <button type="button" onClick={dismissSaveNudge}>暂时不用</button>
              </div>
            </div>
          </article>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="fun-chips" role="toolbar" aria-label="趣味互动">
        {FUN_PROMPTS.map((item) => (
          <button
            key={item.label}
            type="button"
            className="fun-chip"
            disabled={inputDisabled}
            onClick={() => onSendMessage(item.text)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="input-area">
        <label className="sr-only" htmlFor="chat-message-input">给小满发消息</label>
        <textarea
          id="chat-message-input"
          name="message"
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder={
            isNightLocked
              ? "夜间模式已开启，明天见～"
              : isDailyExhausted
              ? "今日使用时间已到，去休息一下吧～"
              : `跟${config.name}说点什么…`
          }
          disabled={inputDisabled}
          className={inputBreathing ? "input-breathing" : ""}
        />
        <button type="button" onClick={send} disabled={inputDisabled} aria-label="发送消息">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="m21 3-7.6 18-3.2-7.2L3 10.6 21 3Z" />
            <path d="m10.2 13.8 4.6-4.6" />
          </svg>
        </button>
      </div>

      {/* 覆盖层 */}
      {(isNightLocked || isDailyExhausted) && (
        <div className="usage-overlay">
          <div className="usage-overlay-card">
            <XiaomanAvatar style={config.style} mode="emotion" emotion="温柔" size="lg" />
            <p className="usage-overlay-text">
              {isNightLocked
                ? "夜间模式已开启，明天见～"
                : "今日使用时间已到，去休息一下吧～"}
            </p>
            <button
              type="button"
              className="usage-overlay-btn"
              onClick={() => {
                // 仅关闭提示，不解除限制（刷新后仍会触发）
                window.location.reload();
              }}
            >
              知道了
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
