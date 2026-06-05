import { apiJson } from "../lib/backend";
import { useEffect, useState } from "react";
import AchievementBadge, { type BadgeInfo } from "../components/AchievementBadge";
import ShareCard, { type ShareCardData } from "../components/ShareCard";

interface GrowthMoment {
  id?: string;
  summary: string;
  timestamp?: string;
  source?: string;
}

interface GrowthData {
  emotional_weather: {
    last_mood?: string;
    trigger?: string;
    since?: string;
    pattern_note?: string;
  };
  emotion_patterns: string[];
  growth_moments: GrowthMoment[];
}

interface GrowthPageProps {
  userId: string;
  onBack: () => void;
  onNavigate?: (view: "report") => void;
}

function formatDate(iso?: string): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  } catch {
    return "";
  }
}

export default function GrowthPage({ userId, onBack, onNavigate }: GrowthPageProps) {
  const [data, setData] = useState<GrowthData | null>(null);
  const [achievements, setAchievements] = useState<BadgeInfo[]>([]);
  const [selectedBadge, setSelectedBadge] = useState<BadgeInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [shareData, setShareData] = useState<ShareCardData | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [recentAchievementId] = useState(() => sessionStorage.getItem("xiaoman_recent_achievement"));

  useEffect(() => {
    if (recentAchievementId) {
      sessionStorage.removeItem("xiaoman_recent_achievement");
    }
  }, [recentAchievementId]);

  useEffect(() => {
    apiJson<GrowthData | null>(`/api/world/${userId}/growth`, null)
      .then((d) => d && setData(d))
      .finally(() => setLoading(false));
  }, [userId]);

  useEffect(() => {
    apiJson<{ achievements?: BadgeInfo[] } | null>(`/api/world/${userId}/achievements`, null).then((d) => {
      if (d?.achievements) {
        setAchievements(d.achievements);
      }
    });
  }, [userId]);

  const weather = data?.emotional_weather;
  const moments = [...(data?.growth_moments || [])].reverse();

  const handleShareBadge = () => {
    if (!selectedBadge) return;
    setShareUrl(null);
    setShareData({ type: "achievement", badge: selectedBadge });
  };

  return (
    <div className="growth-page">
      <header className="subpage-header">
        <button type="button" className="subpage-back" onClick={onBack}>
          ‹
        </button>
        <h1>小满眼中的我</h1>
      </header>

      {loading && <p className="growth-empty">加载中…</p>}

      {/* 成就徽章区 */}
      <section className="growth-badges-section">
        <h2>成就徽章</h2>
        <div className="growth-badges-grid">
          {achievements.length === 0
            ? Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="achievement-badge locked">
                  <div className="badge-icon-wrap">
                    <svg viewBox="0 0 64 64" width="48" height="48">
                      <circle cx="32" cy="32" r="14" fill="none" stroke="#ccc" strokeWidth="3" />
                    </svg>
                  </div>
                  <span className="badge-name">???</span>
                </div>
              ))
            : achievements.map((b) => (
                <AchievementBadge
                  key={b.id}
                  badge={b}
                  onClick={(badge) => setSelectedBadge(badge)}
                  animate={b.id === recentAchievementId}
                />
              ))}
        </div>
      </section>

      {/* 报告入口 */}
      <section className="growth-reports-section">
        <div className="growth-report-card" onClick={() => onNavigate?.("report")}>
          <span className="growth-report-icon">📊</span>
          <span className="growth-report-label">本周情绪报告</span>
          <span className="growth-report-arrow">›</span>
        </div>
        <div className="growth-report-card" onClick={() => onNavigate?.("report")}>
          <span className="growth-report-icon">📅</span>
          <span className="growth-report-label">本月情绪报告</span>
          <span className="growth-report-arrow">›</span>
        </div>
      </section>

      {!loading && weather && (
        <section className="growth-weather-card">
          <h2>情绪天气</h2>
          <p className="growth-weather-mood">{weather.last_mood || "还没聊过"}</p>
          {weather.trigger && (
            <p className="growth-weather-trigger">触发：{weather.trigger}</p>
          )}
          {(data?.emotion_patterns?.length ?? 0) > 0 && (
            <ul className="growth-patterns">
              {data!.emotion_patterns.slice(-3).map((p, i) => (
                <li key={i}>{p}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="growth-timeline">
        <h2>成长节点</h2>
        {moments.length === 0 && !loading && (
          <p className="growth-empty">聊得越多，小满会记下你的重要时刻</p>
        )}
        <ul>
          {moments.map((m, i) => (
            <li key={m.id || i} className="growth-timeline-item">
              <span className="growth-timeline-date">{formatDate(m.timestamp)}</span>
              <p>{m.summary}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* 徽章详情弹窗 */}
      {selectedBadge && (
        <div className="badge-modal-overlay" onClick={() => setSelectedBadge(null)}>
          <div className="badge-modal" onClick={(e) => e.stopPropagation()}>
            <AchievementBadge badge={selectedBadge} />
            <p className="badge-modal-desc">{selectedBadge.description}</p>
            {selectedBadge.unlocked_at && (
              <p className="badge-modal-time">
                解锁于 {new Date(selectedBadge.unlocked_at).toLocaleDateString()}
              </p>
            )}
            <div className="badge-modal-actions">
              <button type="button" className="share-btn" onClick={handleShareBadge}>
                分享
              </button>
              <button type="button" className="badge-modal-close" onClick={() => setSelectedBadge(null)}>
                关闭
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 分享卡片生成 */}
      {shareData && (
        <ShareCard
          data={shareData}
          onGenerated={(url) => setShareUrl(url)}
        />
      )}
      {shareUrl && (
        <div className="share-modal-overlay" onClick={() => { setShareUrl(null); setShareData(null); }}>
          <div className="share-modal" onClick={(e) => e.stopPropagation()}>
            <img src={shareUrl} alt="分享卡片" className="share-preview" />
            <div className="share-modal-actions">
              <a href={shareUrl} download="share-card.png" className="share-download-btn">
                下载图片
              </a>
              <button type="button" className="share-close-btn" onClick={() => { setShareUrl(null); setShareData(null); }}>
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
