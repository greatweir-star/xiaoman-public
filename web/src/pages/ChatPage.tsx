import { apiJson } from "../lib/backend";
import { useState, useEffect, useRef } from "react";
import SkillTree from "../components/SkillTree";
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
  { label: "猜心情", text: "我们来玩猜心情吧~" },
  { label: "猜谜", text: "给我出个谜语猜猜看" },
  { label: "编故事", text: "我们一起编个故事吧，你先开个头" },
] as const;

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
  companionCode,
  todayStatus,
  onAvatarClick,
  userId,
}: ChatPageProps) {
  const [input, setInput] = useState("");
  const [connectionError, setConnectionError] = useState("");
  const [inputBreathing, setInputBreathing] = useState(false);
  const [expandedRecalls, setExpandedRecalls] = useState<Set<number>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [sessionWarnDismissed, setSessionWarnDismissed] = useState(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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
      setConnectionError("连接已断开，正在重连...");
      return;
    }
    onSendMessage(input);
    setInput("");
    setConnectionError("");
  };

  const prevThreshold = skillTree
    ? [0, 20, 50, 100, 200][Math.max(0, skillTree.level - 1)] ?? 0
    : 0;
  const progressCurrent = skillTree ? skillTree.xp - prevThreshold : 0;
  const progressTotal = skillTree ? skillTree.next_threshold - prevThreshold : 20;

  const isNightLocked = usage?.night_locked ?? false;
  const isDailyExhausted = usage !== null && usage.daily_remaining <= 0;
  const showSessionWarn =
    !sessionWarnDismissed && usage !== null && usage.session_remaining <= 5 && usage.session_remaining > 0;
  const inputDisabled = !connected || isNightLocked || isDailyExhausted;

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
              {companionCode && (
                <span className="chat-companion-code">{companionCode}</span>
              )}
              <span className="chat-top-status">
                {isSleeping ? "睡了" : connected ? "在线" : "连接中..."}
                {todayStatus && !isSleeping ? ` · ${todayStatus}` : ""}
              </span>
            </div>
          </div>
          <div className="chat-top-right">
            <div className="status-badge">{xiaomanStatus.activity || "空闲"}</div>
            <div className="mood-badge">{currentEmotion}</div>
          </div>
        </div>
        {skillTree && (
          <div className="chat-header-progress">
            <span className="chat-skill-tree-label">懂我程度</span>
            <SkillTree
              level={skillTree.level}
              name={skillTree.name}
              current={progressCurrent}
              total={Math.max(progressTotal, 1)}
            />
          </div>
        )}
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
                  <div
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
                  </div>
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
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={
            isNightLocked
              ? "夜间模式已开启，明天见～"
              : isDailyExhausted
              ? "今日使用时间已到，去休息一下吧～"
              : `跟${config.name}说点什么...`
          }
          disabled={inputDisabled}
          className={inputBreathing ? "input-breathing" : ""}
        />
        <button type="button" onClick={send} disabled={inputDisabled}>发送</button>
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
