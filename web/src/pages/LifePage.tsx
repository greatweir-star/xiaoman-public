import { apiJson } from "../lib/backend";
import { useState, useEffect } from "react";
import XiaomanAvatar from "../components/XiaomanAvatar";

interface LifePageProps {
  userId: string;
  config: { name: string; style?: string };
  currentEmotion: string;
  onNavigate: (view: "diary" | "memory" | "growth") => void;
  dailyAvatarUrl?: string;
  dailyAvatarLabel?: string;
  dailyAvatarVariant?: string;
  onAvatarClick?: () => void;
}

interface TimelineEntry {
  id: string;
  ts: string;
  type: string;
  title: string;
  detail?: string;
}

const TYPE_LABELS: Record<string, string> = {
  period: "时段",
  diary: "日记",
  chat: "聊天",
  linkage: "联动",
  dreaming: "夜间",
};

function formatTimelineTime(iso: string): string {
  try {
    const d = new Date(iso);
    const mo = (d.getMonth() + 1).toString().padStart(2, "0");
    const day = d.getDate().toString().padStart(2, "0");
    const h = d.getHours().toString().padStart(2, "0");
    const m = d.getMinutes().toString().padStart(2, "0");
    return `${mo}-${day} ${h}:${m}`;
  } catch {
    return iso;
  }
}

export default function LifePage({
  userId,
  config,
  currentEmotion,
  onNavigate,
  dailyAvatarUrl,
  dailyAvatarLabel,
  dailyAvatarVariant,
  onAvatarClick,
}: LifePageProps) {
  const [xiaomanData, setXiaomanData] = useState<any>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [skillTree, setSkillTree] = useState({ level: 1, name: "新同桌", xp: 0, next_threshold: 20 });

  useEffect(() => {
    apiJson<any | null>(`/api/world/${userId}/xiaoman`, null).then((d) => d && setXiaomanData(d));
  }, [userId]);

  useEffect(() => {
    apiJson<{ entries?: TimelineEntry[] }>(`/api/world/${userId}/timeline?limit=40`, { entries: [] }).then((d) => setTimeline(d.entries || []));
  }, [userId]);

  useEffect(() => {
    apiJson<any | null>(`/api/world/${userId}/skill-tree`, null).then((d) => {
      if (d) {
        setSkillTree({
          level: d.level ?? 1,
          name: d.name ?? "\u65b0\u540c\u684c",
          xp: d.xp ?? 0,
          next_threshold: d.next_threshold ?? 20,
        });
      }
    });
  }, [userId]);

  const emotion = xiaomanData?.emotion || {};
  const identity = xiaomanData?.identity || {};
  const signature = identity.catchphrase || "说真的";

  // 进度条计算
  const now = new Date();
  const todayStr = now.toISOString().slice(0, 10);
  const todayChats = timeline.filter((e) => e.type === "chat" && e.ts.startsWith(todayStr)).length;

  const day = now.getDay();
  const diffToMonday = day === 0 ? 6 : day - 1;
  const monday = new Date(now);
  monday.setDate(now.getDate() - diffToMonday);
  monday.setHours(0, 0, 0, 0);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  sunday.setHours(23, 59, 59, 999);

  const chatDates = new Set<string>();
  timeline.forEach((e) => {
    if (e.type === "chat") {
      try {
        const d = new Date(e.ts);
        if (d >= monday && d <= sunday) {
          chatDates.add(e.ts.slice(0, 10));
        }
      } catch {
        // ignore
      }
    }
  });
  const weeklyChatDays = chatDates.size;

  const levelProgress = skillTree.next_threshold > 0
    ? Math.min(100, Math.round((skillTree.xp / skillTree.next_threshold) * 100))
    : 100;

  return (
    <div className="life-page">
      <div className="life-cover">
        <div className="life-cover-bg"></div>
        <div className="life-cover-overlay">
          <div className="life-cover-info">
            <div className="life-cover-text">
              <h2>{config.name}</h2>
              <p className="life-signature">{signature}</p>
              <p className="life-mood-line">{currentEmotion} · 精力{emotion.energy || 50}%</p>
            </div>
            <XiaomanAvatar
              size="lg"
              style={config.style || "fresh"}
              srcOverride={dailyAvatarUrl}
              enlargeable
              title={dailyAvatarLabel ? `今日 · ${dailyAvatarLabel}` : undefined}
              dailyVariant={dailyAvatarVariant}
              onClick={onAvatarClick}
            />
          </div>
        </div>
      </div>

      <div className="life-status-bar">
        <div className="life-stat">
          <span className="life-stat-label">心情</span>
          <div className="life-stat-bar">
            <div style={{ width: `${Math.min(100, (emotion.energy || 50) * 1.2)}%`, background: "#4CAF50" }} />
          </div>
        </div>
        <div className="life-stat">
          <span className="life-stat-label">精力</span>
          <div className="life-stat-bar">
            <div style={{ width: `${emotion.energy || 50}%`, background: "#2196F3" }} />
          </div>
        </div>
      </div>

      <div className="life-progress-section">
        <div className="life-progress-item">
          <div className="life-progress-header">
            <span className="life-progress-label">今日对话</span>
            <span className="life-progress-value">{todayChats}/15 轮</span>
          </div>
          <div className="life-progress-bar">
            <div style={{ width: `${Math.min(100, (todayChats / 15) * 100)}%`, background: "#4CAF50" }} />
          </div>
        </div>
        <div className="life-progress-item">
          <div className="life-progress-header">
            <span className="life-progress-label">本周连续</span>
            <span className="life-progress-value">{weeklyChatDays}/7 天</span>
          </div>
          <div className="life-progress-bar">
            <div style={{ width: `${Math.min(100, (weeklyChatDays / 7) * 100)}%`, background: "#2196F3" }} />
          </div>
        </div>
        <div className="life-progress-item">
          <div className="life-progress-header">
            <span className="life-progress-label">懂我程度 Lv.{skillTree.level} → {skillTree.level + 1}</span>
            <span className="life-progress-value">{skillTree.xp}/{skillTree.next_threshold} XP</span>
          </div>
          <div className="life-progress-bar">
            <div style={{ width: `${levelProgress}%`, background: "#FF9800" }} />
          </div>
        </div>
      </div>

      <section className="life-timeline-section">
        <h3 className="life-timeline-heading">生活时间线</h3>
        {timeline.length === 0 ? (
          <p className="life-timeline-empty">还没有记录，多聊几句或等等小满的一天~</p>
        ) : (
          <ul className="life-timeline-list">
            {timeline.map((entry) => (
              <li key={entry.id} className="life-timeline-item">
                <div className="life-timeline-meta">
                  <span className="life-timeline-type">
                    {TYPE_LABELS[entry.type] || entry.type}
                  </span>
                  <span className="life-timeline-time">{formatTimelineTime(entry.ts)}</span>
                </div>
                <div className="life-timeline-title">{entry.title}</div>
                {entry.detail && (
                  <div className="life-timeline-detail">{entry.detail}</div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="life-menu">
        <div className="life-menu-item" onClick={() => onNavigate("diary")}>
          <span className="life-menu-icon">记</span>
          <span className="life-menu-text">日记</span>
          <span className="life-menu-arrow">›</span>
        </div>
        <div className="life-menu-item" onClick={() => onNavigate("memory")}>
          <span className="life-menu-icon" style={{ background: "#fff3e0", color: "#e65100" }}>忆</span>
          <span className="life-menu-text">记忆库</span>
          <span className="life-menu-arrow">›</span>
        </div>
        <div className="life-menu-item" onClick={() => onNavigate("growth")}>
          <span className="life-menu-icon" style={{ background: "#e8f5e9", color: "#2e7d32" }}>长</span>
          <span className="life-menu-text">成长 · 小满眼中的我</span>
          <span className="life-menu-arrow">›</span>
        </div>
      </div>
    </div>
  );
}
