import { useEffect, useState } from "react";
import XiaomanAvatar from "../components/XiaomanAvatar";
import { apiJson } from "../lib/backend";

interface LifePageProps {
  userId: string;
  config: { name: string; style?: string };
  currentEmotion: string;
  onNavigate: (view: "diary" | "memory" | "growth") => void;
  dailyAvatarUrl?: string;
  dailyAvatarLabel?: string;
  onAvatarClick?: () => void;
}

interface TimelineEntry {
  id: string;
  ts: string;
  type: string;
  title: string;
  detail?: string;
}

interface SkillTree {
  level: number;
  name: string;
  xp: number;
  next_threshold: number;
}

const TYPE_LABELS: Record<string, string> = {
  period: "生活片段",
  diary: "同桌日记",
  chat: "来自聊天",
  linkage: "关系变化",
  dreaming: "夜间记忆",
};

function localDateKey(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function formatTimelineTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const today = localDateKey(new Date());
  const dateKey = localDateKey(date);
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  if (dateKey === today) return `今天 ${hours}:${minutes}`;
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`;
}

export default function LifePage({
  userId,
  config,
  currentEmotion,
  onNavigate,
  dailyAvatarUrl,
  dailyAvatarLabel,
  onAvatarClick,
}: LifePageProps) {
  const [xiaomanData, setXiaomanData] = useState<any>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [skillTree, setSkillTree] = useState<SkillTree>({
    level: 1,
    name: "新同桌",
    xp: 0,
    next_threshold: 20,
  });

  useEffect(() => {
    let active = true;
    Promise.all([
      apiJson<any | null>(`/api/world/${userId}/xiaoman`, null),
      apiJson<{ entries?: TimelineEntry[] }>(`/api/world/${userId}/timeline?limit=40`, { entries: [] }),
      apiJson<any | null>(`/api/world/${userId}/skill-tree`, null),
    ]).then(([world, timelineData, tree]) => {
      if (!active) return;
      if (world) setXiaomanData(world);
      setTimeline(timelineData.entries || []);
      if (tree) {
        setSkillTree({
          level: tree.level ?? 1,
          name: tree.name ?? "新同桌",
          xp: tree.xp ?? 0,
          next_threshold: tree.next_threshold ?? 20,
        });
      }
    });
    return () => {
      active = false;
    };
  }, [userId]);

  const identity = xiaomanData?.identity || {};
  const signature = identity.catchphrase || "慢一点也没关系，我在听。";
  const today = localDateKey(new Date());
  const todayEntries = timeline.filter((entry) => localDateKey(new Date(entry.ts)) === today);
  const todayChats = todayEntries.filter((entry) => entry.type === "chat").length;
  const memoryCount = timeline.filter((entry) => entry.type === "chat" || entry.type === "linkage").length;
  const levelProgress = skillTree.next_threshold > 0
    ? Math.min(100, Math.round((skillTree.xp / skillTree.next_threshold) * 100))
    : 100;

  return (
    <div className="life-page story-page">
      <header className="story-page-header">
        <div>
          <p className="soft-eyebrow">STORY</p>
          <h2>我们的故事</h2>
        </div>
        <button type="button" className="story-header-action" aria-label="查看关系收藏">
          ♡
        </button>
      </header>

      <article className="story-relationship-card">
        <XiaomanAvatar
          size="lg"
          style={config.style || "fresh"}
          srcOverride={dailyAvatarUrl}
          enlargeable
          title={dailyAvatarLabel ? `今日 · ${dailyAvatarLabel}` : undefined}
          onClick={onAvatarClick}
        />
        <div>
          <span className="story-chip">关系 Lv.{skillTree.level}</span>
          <h3>她正在慢慢懂你</h3>
          <p>{signature}</p>
        </div>
      </article>

      <section className="story-section">
        <div className="story-section-heading">
          <div>
            <p className="soft-eyebrow">TODAY</p>
            <h3>今天留下的片段</h3>
          </div>
          <button type="button" onClick={() => onNavigate("diary")}>查看日记</button>
        </div>
        <div className="story-fragment-grid">
          <article className="story-fragment-card story-fragment-card-warm">
            <span>聊过的事</span>
            <p>{todayChats > 0 ? `今天已经留下 ${todayChats} 个聊天片段。` : "今天的故事还没开始，去和小满说两句吧。"}</p>
          </article>
          <article className="story-fragment-card story-fragment-card-cool">
            <span>情绪天气</span>
            <p>今天是{currentEmotion || "平静"}的一天，小满会跟着你的节奏慢慢来。</p>
          </article>
        </div>
      </section>

      <section className="story-section">
        <div className="story-section-heading">
          <div>
            <p className="soft-eyebrow">GROWTH</p>
            <h3>关系正在生长</h3>
          </div>
          <span className="story-chip">Lv.{skillTree.level} {skillTree.name}</span>
        </div>
        <div className="story-growth-card">
          <div className="story-growth-copy">
            <span>距离下一阶段还有一点点</span>
            <strong>{levelProgress}%</strong>
          </div>
          <div className="story-progress" aria-label={`关系成长进度 ${levelProgress}%`}>
            <span style={{ width: `${levelProgress}%` }} />
          </div>
        </div>
        <div className="story-metric-grid">
          <button type="button" onClick={() => onNavigate("memory")}>
            <strong>{memoryCount}</strong>
            <span>记忆片段</span>
          </button>
          <button type="button" onClick={() => onNavigate("growth")}>
            <strong>{Math.max(0, skillTree.level - 1)}</strong>
            <span>成长节点</span>
          </button>
          <button type="button" onClick={() => onNavigate("diary")}>
            <strong>{timeline.filter((entry) => entry.type === "diary").length}</strong>
            <span>同桌日记</span>
          </button>
        </div>
      </section>

      <section className="story-section story-timeline-section">
        <div className="story-section-heading">
          <div>
            <p className="soft-eyebrow">TIMELINE</p>
            <h3>最近发生的事</h3>
          </div>
        </div>
        {timeline.length === 0 ? (
          <p className="story-empty">还没有记录。多聊几句，你们的故事会从这里慢慢长出来。</p>
        ) : (
          <ul className="story-timeline">
            {timeline.slice(0, 8).map((entry) => (
              <li key={entry.id}>
                <span className="story-timeline-dot" />
                <div>
                  <strong>{entry.title}</strong>
                  <span>{TYPE_LABELS[entry.type] || entry.type} · {formatTimelineTime(entry.ts)}</span>
                  {entry.detail ? <p>{entry.detail}</p> : null}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
