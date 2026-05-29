/** 同桌设定形象（onboarding 画风），与情绪 emoji 占位图区分 */

export const COMPANION_STYLES = ["fresh", "korean", "watercolor"] as const;
export type CompanionStyle = (typeof COMPANION_STYLES)[number];

export const COMPANION_STYLE_OPTIONS: {
  id: CompanionStyle;
  label: string;
  desc: string;
}[] = [
  { id: "fresh", label: "清新动画", desc: "日系动画，新海诚式柔和光线" },
  { id: "korean", label: "韩系插画", desc: "时尚插画，干净线条" },
  { id: "watercolor", label: "温柔水彩", desc: "手绘质感，pastel色调" },
];

const EMOTION_AVATAR_RE = /\/avatars\/[^/]+\.svg$/i;

export function isEmotionPlaceholderUrl(url?: string | null): boolean {
  if (!url) return false;
  return EMOTION_AVATAR_RE.test(url);
}

/** 按优先级尝试的设定形象 URL（PNG 资源就绪后自动优先） */
export function stylePortraitCandidates(style: string): string[] {
  const id = (COMPANION_STYLES as readonly string[]).includes(style) ? style : "fresh";
  return [
    `/assets/xiaoman/styles/${id}.png`,
    `/assets/xiaoman/avatar_small.jpg`,
    `/styles/${id}.svg`,
    `/styles/fresh.svg`,
  ];
}

export function resolveCompanionPortraitUrl(
  style: string,
  dailyUrl?: string | null,
): string {
  if (dailyUrl && !isEmotionPlaceholderUrl(dailyUrl)) return dailyUrl;
  return stylePortraitCandidates(style)[0];
}

export function emotionAvatarUrl(emotion?: string): string | undefined {
  if (!emotion?.trim()) return undefined;
  return `/avatars/${emotion.trim()}.svg`;
}
