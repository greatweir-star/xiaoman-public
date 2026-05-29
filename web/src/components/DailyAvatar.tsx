import { useMemo, type ReactNode } from "react";

interface DailyAvatarProps {
  emotion?: string;
  size?: number;
  userId?: string;
}

const SEASONS = [
  { name: "spring", bg: "#FFE4E1", label: "春日", months: [2, 3, 4] },
  { name: "summer", bg: "#E0F7FA", label: "夏日", months: [5, 6, 7] },
  { name: "autumn", bg: "#FFF3E0", label: "秋日", months: [8, 9, 10] },
  { name: "winter", bg: "#F5F5F5", label: "冬日", months: [11, 0, 1] },
];

const ACCESSORIES = [
  { id: "scarf", season: "winter", svg: <path d="M20 38 Q32 46 44 38" stroke="#FF8A65" strokeWidth="4" fill="none" strokeLinecap="round" /> },
  { id: "hat", season: "summer", svg: <ellipse cx="32" cy="18" rx="18" ry="6" fill="#FFD54F" /> },
  { id: "glasses", season: "any", svg: <><circle cx="24" cy="26" r="5" fill="none" stroke="#555" strokeWidth="2" /><circle cx="40" cy="26" r="5" fill="none" stroke="#555" strokeWidth="2" /><line x1="29" y1="26" x2="35" y2="26" stroke="#555" strokeWidth="2" /></> },
  { id: "ribbon", season: "spring", svg: <path d="M26 12 L32 18 L38 12 L32 24 Z" fill="#F48FB1" /> },
  { id: "backpack", season: "autumn", svg: <rect x="22" y="40" width="20" height="14" rx="3" fill="#A1887F" /> },
];

function hashString(str: string): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = (h << 5) - h + str.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

function getSeason() {
  const m = new Date().getMonth();
  return SEASONS.find((s) => s.months.includes(m)) || SEASONS[0];
}

function getEmotionMouth(emotion?: string): ReactNode {
  const e = emotion || "";
  if (["开心", "兴奋", "激动", "幸福"].some((k) => e.includes(k))) {
    return <path d="M24 36 Q32 44 40 36" stroke="#555" strokeWidth="2" fill="none" strokeLinecap="round" />;
  }
  if (["难过", "委屈", "丧", "崩溃", "绝望", "痛苦"].some((k) => e.includes(k))) {
    return <path d="M24 40 Q32 34 40 40" stroke="#555" strokeWidth="2" fill="none" strokeLinecap="round" />;
  }
  if (["惊讶", "震惊"].some((k) => e.includes(k))) {
    return <circle cx="32" cy="38" r="3" fill="#555" />;
  }
  // 默认微笑
  return <path d="M26 38 Q32 42 38 38" stroke="#555" strokeWidth="2" fill="none" strokeLinecap="round" />;
}

function getEmotionEyes(emotion?: string): ReactNode {
  const e = emotion || "";
  if (["困倦", "睡了", "累"].some((k) => e.includes(k))) {
    return (
      <>
        <line x1="22" y1="26" x2="28" y2="26" stroke="#555" strokeWidth="2" strokeLinecap="round" />
        <line x1="36" y1="26" x2="42" y2="26" stroke="#555" strokeWidth="2" strokeLinecap="round" />
      </>
    );
  }
  if (["惊讶", "震惊"].some((k) => e.includes(k))) {
    return (
      <>
        <circle cx="25" cy="26" r="4" fill="#555" />
        <circle cx="39" cy="26" r="4" fill="#555" />
      </>
    );
  }
  return (
    <>
      <circle cx="25" cy="26" r="3" fill="#555" />
      <circle cx="39" cy="26" r="3" fill="#555" />
    </>
  );
}

function SeasonBackground({ season }: { season: (typeof SEASONS)[0] }) {
  const elements: ReactNode[] = [];
  if (season.name === "spring") {
    for (let i = 0; i < 6; i++) {
      const x = 10 + i * 16;
      const y = 10 + (i % 3) * 18;
      elements.push(<path key={i} d={`M${x} ${y} Q${x + 4} ${y - 6} ${x + 8} ${y} Q${x + 4} ${y + 6} ${x} ${y}`} fill="#F8BBD0" opacity="0.6" />);
    }
  } else if (season.name === "summer") {
    elements.push(<circle key="sun" cx="52" cy="14" r="8" fill="#FFD54F" opacity="0.5" />);
    for (let i = 0; i < 4; i++) {
      elements.push(<line key={i} x1={12 + i * 12} y1="52" x2={16 + i * 12} y2="52" stroke="#81D4FA" strokeWidth="2" opacity="0.5" />);
    }
  } else if (season.name === "autumn") {
    for (let i = 0; i < 5; i++) {
      const x = 12 + i * 14;
      const y = 12 + (i % 2) * 10;
      elements.push(<path key={i} d={`M${x} ${y} Q${x + 3} ${y + 6} ${x} ${y + 10} Q${x - 3} ${y + 6} ${x} ${y}`} fill="#FFCC80" opacity="0.6" />);
    }
  } else {
    for (let i = 0; i < 6; i++) {
      const x = 10 + i * 14;
      const y = 8 + (i % 3) * 14;
      elements.push(<circle key={i} cx={x} cy={y} r="1.5" fill="#B0BEC5" opacity="0.5" />);
    }
  }
  return <>{elements}</>;
}

export default function DailyAvatar({ emotion, size = 120, userId = "" }: DailyAvatarProps) {
  const season = useMemo(() => getSeason(), []);
  const accessory = useMemo(() => {
    const day = new Date().toISOString().slice(0, 10);
    const hash = hashString(`${userId}:${day}`);
    const pool = ACCESSORIES.filter((a) => a.season === "any" || a.season === season.name);
    return pool[hash % pool.length] || ACCESSORIES[2];
  }, [userId, season.name]);

  const s = size;

  return (
    <svg width={s} height={s} viewBox="0 0 64 64" style={{ borderRadius: "50%", background: season.bg }}>
      <SeasonBackground season={season} />
      {/* 脸 */}
      <circle cx="32" cy="32" r="18" fill="#FFE0B2" />
      {/* 腮红 */}
      <circle cx="22" cy="34" r="3" fill="#FFAB91" opacity="0.4" />
      <circle cx="42" cy="34" r="3" fill="#FFAB91" opacity="0.4" />
      {/* 眼睛 */}
      {getEmotionEyes(emotion)}
      {/* 嘴 */}
      {getEmotionMouth(emotion)}
      {/* 配饰 */}
      {accessory.svg}
    </svg>
  );
}

export function getTodayAvatarKey(userId: string): string {
  const day = new Date().toISOString().slice(0, 10);
  const season = getSeason().name;
  const hash = hashString(`${userId}:${day}`);
  const pool = ACCESSORIES.filter((a) => a.season === "any" || a.season === season);
  const acc = pool[hash % pool.length];
  return `${day}-${season}-${acc?.id ?? "none"}`;
}
