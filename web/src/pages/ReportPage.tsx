import { apiJson } from "../lib/backend";
import { useEffect, useState, useMemo } from "react";
import ShareCard, { type ShareCardData } from "../components/ShareCard";

interface EmotionTrendItem {
  date: string;
  emotion: string;
  value: number;
}

interface ReportData {
  period: "weekly" | "monthly";
  start_date?: string;
  end_date?: string;
  month?: string;
  generated_at: string;
  emotion_trend: (EmotionTrendItem | null)[];
  top_emotions: { label: string; count: number }[];
  keyword_cloud?: { word: string; count: number }[];
  chat_days: number;
  total_chat_turns: number;
  xiaoman_note: string;
  achievements_unlocked?: number;
  level_change?: { from: number; to: number };
}

interface ReportPageProps {
  userId: string;
  onBack: () => void;
  initialPeriod?: "weekly" | "monthly";
}

function formatShortDate(iso: string): string {
  try {
    const d = new Date(iso + "T00:00:00");
    return `${d.getMonth() + 1}/${d.getDate()}`;
  } catch {
    return iso.slice(5);
  }
}

function emotionColor(value: number): string {
  if (value >= 15) return "#4CAF50";
  if (value >= 5) return "#8BC34A";
  if (value >= -5) return "#FFC107";
  if (value >= -15) return "#FF9800";
  return "#F44336";
}

function generateSmoothPath(points: { x: number; y: number }[]): string {
  if (points.length === 0) return "";
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[Math.max(0, i - 1)];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[Math.min(points.length - 1, i + 2)];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
  }
  return d;
}

function EmotionChart({ data }: { data: (EmotionTrendItem | null)[] }) {
  const valid = useMemo(() => {
    return data
      .map((d, i) => (d ? { index: i, ...d } : null))
      .filter(Boolean) as Array<{ index: number; date: string; emotion: string; value: number }>;
  }, [data]);

  if (valid.length === 0) {
    return (
      <div className="report-chart-empty">
        还没有足够的情绪数据，多聊几句再来查看吧～
      </div>
    );
  }

  const width = 340;
  const height = 180;
  const padding = { top: 20, right: 16, bottom: 32, left: 32 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;
  const minV = -50;
  const maxV = 50;

  const points = valid.map((d) => {
    const x = padding.left + (d.index / (data.length - 1 || 1)) * chartW;
    const y = padding.top + chartH - ((d.value - minV) / (maxV - minV)) * chartH;
    return { x, y, value: d.value, date: d.date };
  });

  const linePath = generateSmoothPath(points);
  const areaPath = `${linePath} L ${points[points.length - 1].x} ${padding.top + chartH} L ${points[0].x} ${padding.top + chartH} Z`;

  const yTicks = [-40, -20, 0, 20, 40];
  const xTicks = data.length <= 7 ? data.map((_, i) => i) : [0, Math.floor(data.length / 2), data.length - 1];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="report-chart-svg">
      <defs>
        <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#667eea" stopOpacity="0.25" />
          <stop offset="100%" stopColor="#667eea" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {/* 网格线 */}
      {yTicks.map((v) => {
        const y = padding.top + chartH - ((v - minV) / (maxV - minV)) * chartH;
        return (
          <line key={v} x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#eee" strokeWidth="1" />
        );
      })}
      {/* 零线 */}
      <line
        x1={padding.left}
        y1={padding.top + chartH - ((0 - minV) / (maxV - minV)) * chartH}
        x2={width - padding.right}
        y2={padding.top + chartH - ((0 - minV) / (maxV - minV)) * chartH}
        stroke="#ccc"
        strokeWidth="1"
        strokeDasharray="4 3"
      />
      {/* Y轴标签 */}
      {yTicks.map((v) => {
        const y = padding.top + chartH - ((v - minV) / (maxV - minV)) * chartH;
        return (
          <text key={`y${v}`} x={padding.left - 6} y={y + 4} textAnchor="end" fontSize="10" fill="#999">
            {v}
          </text>
        );
      })}
      {/* X轴标签 */}
      {xTicks.map((i) => {
        const x = padding.left + (i / (data.length - 1 || 1)) * chartW;
        const d = data[i];
        return (
          <text key={`x${i}`} x={x} y={height - 8} textAnchor="middle" fontSize="10" fill="#999">
            {d ? formatShortDate(d.date) : ""}
          </text>
        );
      })}
      {/* 填充区域 */}
      <path d={areaPath} fill="url(#areaFill)" />
      {/* 折线 */}
      <path d={linePath} fill="none" stroke="#667eea" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      {/* 数据点 */}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="4" fill="#fff" stroke={emotionColor(p.value)} strokeWidth="2.5" />
        </g>
      ))}
    </svg>
  );
}

export default function ReportPage({ userId, onBack, initialPeriod = "weekly" }: ReportPageProps) {
  const [period, setPeriod] = useState<"weekly" | "monthly">(initialPeriod);
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [shareData, setShareData] = useState<ShareCardData | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    apiJson<ReportData | null>(`/api/world/${userId}/reports/${period}`, null)
      .then((d) => d && setReport(d))
      .finally(() => setLoading(false));
  }, [userId, period]);

  const title = period === "weekly" ? "本周情绪报告" : "本月情绪报告";
  const note = report?.xiaoman_note || "";

  const handleShare = () => {
    if (!report) return;
    setShareUrl(null);
    setShareData({
      type: "report",
      report: {
        period: report.period,
        top_emotions: report.top_emotions,
        xiaoman_note: report.xiaoman_note,
      },
    });
  };

  return (
    <div className="report-page">
      <header className="subpage-header">
        <button type="button" className="subpage-back" onClick={onBack}>
          ‹
        </button>
        <h1>{title}</h1>
        <button type="button" className="report-share-btn" onClick={handleShare} disabled={!report || loading}>
          分享
        </button>
      </header>

      <div className="report-tabs">
        <button
          type="button"
          className={period === "weekly" ? "active" : ""}
          onClick={() => setPeriod("weekly")}
        >
          本周
        </button>
        <button
          type="button"
          className={period === "monthly" ? "active" : ""}
          onClick={() => setPeriod("monthly")}
        >
          本月
        </button>
      </div>

      <div className="report-content">
        {loading && <p className="report-loading">加载中…</p>}

        {!loading && report && (
          <>
            {/* 情绪折线图 */}
            <section className="report-section">
              <h2>情绪走势</h2>
              <div className="report-chart-wrap">
                <EmotionChart data={report.emotion_trend} />
              </div>
            </section>

            {/* 统计 */}
            <section className="report-section report-stats">
              <div className="report-stat">
                <span className="report-stat-num">{report.chat_days}</span>
                <span className="report-stat-label">
                  {period === "weekly" ? "本周对话天数" : "本月对话天数"}
                </span>
              </div>
              <div className="report-stat">
                <span className="report-stat-num">{report.total_chat_turns}</span>
                <span className="report-stat-label">对话轮次</span>
              </div>
              {period === "monthly" && typeof report.achievements_unlocked === "number" && (
                <div className="report-stat">
                  <span className="report-stat-num">{report.achievements_unlocked}</span>
                  <span className="report-stat-label">新解锁成就</span>
                </div>
              )}
            </section>

            {/* 高频情绪标签 */}
            {report.top_emotions.length > 0 && (
              <section className="report-section">
                <h2>高频情绪</h2>
                <div className="report-tags">
                  {report.top_emotions.map((e) => (
                    <span key={e.label} className="report-tag">
                      {e.label} ×{e.count}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {/* 关键词云（月报） */}
            {period === "monthly" && report.keyword_cloud && report.keyword_cloud.length > 0 && (
              <section className="report-section">
                <h2>月度关键词</h2>
                <div className="report-tags">
                  {report.keyword_cloud.map((k) => (
                    <span key={k.word} className="report-tag report-tag-cloud">
                      {k.word}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {/* 小满的话 */}
            {note && (
              <section className="report-section">
                <h2>小满的话</h2>
                <blockquote className="report-note">{note}</blockquote>
              </section>
            )}
          </>
        )}

        {!loading && !report && (
          <p className="report-loading">报告生成失败，请稍后再试</p>
        )}
      </div>

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
