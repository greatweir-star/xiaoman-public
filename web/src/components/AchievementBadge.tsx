import { useState, useEffect } from "react";

export interface BadgeInfo {
  id: string;
  name: string;
  description: string;
  level: "bronze" | "silver" | "gold";
  unlocked: boolean;
  unlocked_at?: string | null;
}

interface AchievementBadgeProps {
  badge: BadgeInfo;
  onClick?: (badge: BadgeInfo) => void;
  animate?: boolean;
}

const GRADIENTS: Record<string, [string, string]> = {
  bronze: ["#CD7F32", "#B87333"],
  silver: ["#C0C0C0", "#A8A8A8"],
  gold: ["#FFD700", "#DAA520"],
};

function BadgeIcon({ id, color }: { id: string; color: string }) {
  switch (id) {
    case "first_vent":
      // 雨滴落入水面的涟漪
      return (
        <svg viewBox="0 0 64 64" width="48" height="48">
          <defs>
            <radialGradient id="rippleG" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor={color} stopOpacity="0.3" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </radialGradient>
          </defs>
          <ellipse cx="32" cy="48" rx="24" ry="6" fill="url(#rippleG)" />
          <ellipse cx="32" cy="48" rx="16" ry="4" fill="none" stroke={color} strokeWidth="1.5" opacity="0.6" />
          <ellipse cx="32" cy="48" rx="8" ry="2" fill="none" stroke={color} strokeWidth="1.5" opacity="0.8" />
          <path d="M32 16 Q34 28 32 40 Q30 28 32 16" fill={color} />
        </svg>
      );
    case "secret_guardian":
      // 带心形锁的锁
      return (
        <svg viewBox="0 0 64 64" width="48" height="48">
          <rect x="18" y="26" width="28" height="22" rx="3" fill={color} />
          <path d="M22 26 V18 A10 10 0 0 1 42 18 V26" fill="none" stroke={color} strokeWidth="3.5" strokeLinecap="round" />
          <path d="M32 34 Q28 30 28 34 Q28 38 32 42 Q36 38 36 34 Q36 30 32 34" fill="#fff" opacity="0.9" />
        </svg>
      );
    case "companion_7d":
      // 彩虹桥
      return (
        <svg viewBox="0 0 64 64" width="48" height="48">
          <path d="M8 48 Q32 8 56 48" fill="none" stroke={color} strokeWidth="3.5" strokeLinecap="round" opacity="0.35" />
          <path d="M12 48 Q32 16 52 48" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" opacity="0.55" />
          <path d="M16 48 Q32 24 48 48" fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" opacity="0.75" />
          <path d="M20 48 Q32 32 44 48" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );
    case "exam_buddy":
      // 打开的书本 + 铅笔
      return (
        <svg viewBox="0 0 64 64" width="48" height="48">
          <path d="M8 20 Q18 14 32 20 Q46 14 56 20 V48 Q46 42 32 48 Q18 42 8 48 Z" fill={color} opacity="0.9" />
          <line x1="32" y1="20" x2="32" y2="48" stroke="#fff" strokeWidth="1.5" opacity="0.6" />
          <rect x="52" y="12" width="6" height="28" rx="1" fill={color} opacity="0.7" />
          <polygon points="55,8 58,12 52,12" fill={color} opacity="0.7" />
        </svg>
      );
    case "emotion_stable":
      // 太阳
      return (
        <svg viewBox="0 0 64 64" width="48" height="48">
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
      // 向上生长的树苗
      return (
        <svg viewBox="0 0 64 64" width="48" height="48">
          <path d="M32 52 V32" stroke={color} strokeWidth="3" strokeLinecap="round" />
          <path d="M32 40 Q20 34 16 24 Q24 28 32 36" fill={color} opacity="0.85" />
          <path d="M32 32 Q44 26 48 16 Q40 20 32 28" fill={color} opacity="0.85" />
          <ellipse cx="32" cy="54" rx="8" ry="3" fill={color} opacity="0.25" />
        </svg>
      );
    default:
      return (
        <svg viewBox="0 0 64 64" width="48" height="48">
          <circle cx="32" cy="32" r="14" fill="none" stroke={color} strokeWidth="3" />
        </svg>
      );
  }
}

export default function AchievementBadge({ badge, onClick, animate }: AchievementBadgeProps) {
  const [animating, setAnimating] = useState(animate && badge.unlocked);

  useEffect(() => {
    if (animate && badge.unlocked) {
      setAnimating(true);
      const timer = setTimeout(() => setAnimating(false), 600);
      return () => clearTimeout(timer);
    }
  }, [animate, badge.unlocked]);

  const unlocked = badge.unlocked;
  const [c1] = GRADIENTS[badge.level] || GRADIENTS.bronze;
  const color = unlocked ? c1 : "#ccc";

  return (
    <button
      type="button"
      className={`achievement-badge ${unlocked ? "unlocked" : "locked"} ${animating ? "animate-unlock" : ""}`}
      onClick={() => unlocked && onClick?.(badge)}
      disabled={!unlocked}
      title={unlocked ? badge.name : "???"}
    >
      <div className="badge-icon-wrap">
        <BadgeIcon id={badge.id} color={color} />
        {!unlocked && (
          <div className="badge-lock-overlay">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="#999">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
            </svg>
          </div>
        )}
      </div>
      <span className="badge-name">{unlocked ? badge.name : "???"}</span>
      <span className="badge-level">{unlocked ? badge.level.toUpperCase() : ""}</span>
    </button>
  );
}
