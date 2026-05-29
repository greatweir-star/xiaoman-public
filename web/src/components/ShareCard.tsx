import { useRef, useEffect } from "react";
import { toPng } from "html-to-image";
import type { BadgeInfo } from "./AchievementBadge";

interface ReportShareData {
  period: "weekly" | "monthly";
  top_emotions: { label: string; count: number }[];
  xiaoman_note: string;
}

export interface ShareCardData {
  type: "achievement" | "report" | "levelup";
  badge?: BadgeInfo;
  report?: ReportShareData;
  levelup?: { from: number; to: number; date: string };
}

interface ShareCardProps {
  data: ShareCardData;
  onGenerated?: (dataUrl: string) => void;
  onError?: (err: Error) => void;
}

const SCENES: Record<string, { bg: string; accent: string; label: string }> = {
  achievement: { bg: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", accent: "#ffd700", label: "我和小满的故事" },
  report: { bg: "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)", accent: "#fff", label: "" },
  levelup: { bg: "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)", accent: "#fff", label: "我们升级了！" },
};

function BadgeSVG({ id, color }: { id: string; color: string }) {
  // 简化版徽章图标，与 AchievementBadge 保持一致
  switch (id) {
    case "first_vent":
      return (
        <svg viewBox="0 0 64 64" width="80" height="80">
          <ellipse cx="32" cy="48" rx="24" ry="6" fill={color} opacity="0.3" />
          <ellipse cx="32" cy="48" rx="16" ry="4" fill="none" stroke={color} strokeWidth="1.5" opacity="0.6" />
          <ellipse cx="32" cy="48" rx="8" ry="2" fill="none" stroke={color} strokeWidth="1.5" opacity="0.8" />
          <path d="M32 16 Q34 28 32 40 Q30 28 32 16" fill={color} />
        </svg>
      );
    case "secret_guardian":
      return (
        <svg viewBox="0 0 64 64" width="80" height="80">
          <rect x="18" y="26" width="28" height="22" rx="3" fill={color} />
          <path d="M22 26 V18 A10 10 0 0 1 42 18 V26" fill="none" stroke={color} strokeWidth="3.5" strokeLinecap="round" />
          <path d="M32 34 Q28 30 28 34 Q28 38 32 42 Q36 38 36 34 Q36 30 32 34" fill="#fff" opacity="0.9" />
        </svg>
      );
    case "companion_7d":
      return (
        <svg viewBox="0 0 64 64" width="80" height="80">
          <path d="M8 48 Q32 8 56 48" fill="none" stroke={color} strokeWidth="3.5" strokeLinecap="round" opacity="0.35" />
          <path d="M12 48 Q32 16 52 48" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" opacity="0.55" />
          <path d="M16 48 Q32 24 48 48" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.75" />
          <path d="M20 48 Q32 32 44 48" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );
    case "exam_buddy":
      return (
        <svg viewBox="0 0 64 64" width="80" height="80">
          <path d="M8 20 Q18 14 32 20 Q46 14 56 20 V48 Q46 42 32 48 Q18 42 8 48 Z" fill={color} opacity="0.9" />
          <line x1="32" y1="20" x2="32" y2="48" stroke="#fff" strokeWidth="1.5" opacity="0.6" />
          <rect x="52" y="12" width="6" height="28" rx="1" fill={color} opacity="0.7" />
          <polygon points="55,8 58,12 52,12" fill={color} opacity="0.7" />
        </svg>
      );
    case "emotion_stable":
      return (
        <svg viewBox="0 0 64 64" width="80" height="80">
          <circle cx="32" cy="32" r="10" fill={color} />
          {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => {
            const rad = (deg * Math.PI) / 180;
            const x1 = 32 + Math.cos(rad) * 14;
            const y1 = 32 + Math.sin(rad) * 14;
            const x2 = 32 + Math.cos(rad) * 20;
            const y2 = 32 + Math.sin(rad) * 20;
            return <line key={deg} x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth="2.5" strokeLinecap="round" />;
          })}
        </svg>
      );
    case "growth_witness":
      return (
        <svg viewBox="0 0 64 64" width="80" height="80">
          <path d="M32 52 V32" stroke={color} strokeWidth="3" strokeLinecap="round" />
          <path d="M32 40 Q20 34 16 24 Q24 28 32 36" fill={color} opacity="0.85" />
          <path d="M32 32 Q44 26 48 16 Q40 20 32 28" fill={color} opacity="0.85" />
          <ellipse cx="32" cy="54" rx="8" ry="3" fill={color} opacity="0.25" />
        </svg>
      );
    default:
      return (
        <svg viewBox="0 0 64 64" width="80" height="80">
          <circle cx="32" cy="32" r="14" fill="none" stroke={color} strokeWidth="3" />
        </svg>
      );
  }
}

export default function ShareCard({ data, onGenerated, onError }: ShareCardProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    // 延迟一帧确保字体/布局稳定
    const timer = setTimeout(() => {
      toPng(ref.current!, { width: 1080, height: 608, pixelRatio: 2, cacheBust: true })
        .then((dataUrl) => {
          onGenerated?.(dataUrl);
        })
        .catch((err) => {
          onError?.(err);
        });
    }, 100);
    return () => clearTimeout(timer);
  }, [data, onGenerated, onError]);

  const scene = SCENES[data.type];
  const dateStr = new Date().toLocaleDateString("zh-CN", { year: "numeric", month: "long", day: "numeric" });

  let content: React.ReactNode = null;
  if (data.type === "achievement" && data.badge) {
    const color = data.badge.level === "gold" ? "#FFD700" : data.badge.level === "silver" ? "#C0C0C0" : "#CD7F32";
    content = (
      <>
        <div style={{ marginBottom: 24 }}>
          <BadgeSVG id={data.badge.id} color={color} />
        </div>
        <h2 style={{ fontSize: 48, margin: "0 0 12px", fontWeight: 700 }}>{data.badge.name}</h2>
        <p style={{ fontSize: 24, margin: 0, opacity: 0.9 }}>{data.badge.description}</p>
        <p style={{ fontSize: 20, margin: "16px 0 0", opacity: 0.75 }}>{dateStr}</p>
      </>
    );
  } else if (data.type === "report" && data.report) {
    const top3 = data.report.top_emotions.slice(0, 3);
    content = (
      <>
        <h2 style={{ fontSize: 44, margin: "0 0 12px", fontWeight: 700 }}>
          {data.report.period === "weekly" ? "本周情绪报告" : "本月情绪报告"}
        </h2>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", marginBottom: 16 }}>
          {top3.map((e) => (
            <span key={e.label} style={{ fontSize: 22, background: "rgba(255,255,255,0.2)", padding: "6px 16px", borderRadius: 20 }}>
              {e.label} ×{e.count}
            </span>
          ))}
        </div>
        <p style={{ fontSize: 22, margin: 0, opacity: 0.9, maxWidth: 700, lineHeight: 1.5 }}>{data.report.xiaoman_note}</p>
      </>
    );
  } else if (data.type === "levelup" && data.levelup) {
    content = (
      <>
        <h2 style={{ fontSize: 48, margin: "0 0 12px", fontWeight: 700 }}>
          L{data.levelup.from} → L{data.levelup.to}
        </h2>
        <p style={{ fontSize: 28, margin: 0, opacity: 0.9 }}>我们升级了！</p>
        <p style={{ fontSize: 20, margin: "16px 0 0", opacity: 0.75 }}>{data.levelup.date}</p>
      </>
    );
  }

  return (
    <div style={{ position: "absolute", left: -9999, top: -9999, overflow: "hidden" }}>
      <div
        ref={ref}
        style={{
          width: 1080,
          height: 608,
          background: scene.bg,
          color: "#fff",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
          position: "relative",
          padding: 48,
          boxSizing: "border-box",
        }}
      >
        {/* 小满头像占位（左上角） */}
        <div style={{ position: "absolute", top: 32, left: 32, display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 56, height: 56, borderRadius: "50%", background: "rgba(255,255,255,0.25)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28 }}>
            满
          </div>
          <span style={{ fontSize: 22, fontWeight: 600 }}>小满</span>
        </div>

        {/* 主内容 */}
        {content}

        {/* 底部签名 */}
        <div style={{ position: "absolute", bottom: 32, left: 32, fontSize: 20, opacity: 0.8 }}>
          {scene.label}
        </div>

        {/* 二维码占位 */}
        <div
          style={{
            position: "absolute",
            bottom: 32,
            right: 32,
            width: 96,
            height: 96,
            background: "rgba(255,255,255,0.2)",
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
          }}
        >
          二维码
        </div>
      </div>
    </div>
  );
}
