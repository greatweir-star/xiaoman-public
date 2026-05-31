import avatarAssets from "../config/xiaoman-avatar-assets.json";

export type CompanionStyle = "fresh" | "korean" | "watercolor";

interface StyleAssetConfig {
  id: CompanionStyle;
  label: string;
  desc: string;
  preview: string;
  portrait: string;
  onboarding?: string;
}

interface AvatarAssetConfig {
  version: number;
  assetRoot: string;
  defaultStyle: CompanionStyle;
  fallbackPortrait: string;
  legacyAliases?: Record<string, string>;
  onboarding: {
    splash: string;
  };
  styles: StyleAssetConfig[];
  emotions: Record<string, string>;
}

const config = avatarAssets as AvatarAssetConfig;
const assetRoot = config.assetRoot.replace(/\/$/, "");

function assetUrl(path: string): string {
  return `${assetRoot}/${path.replace(/^\//, "")}`;
}

export function normalizeAvatarAssetUrl(url?: string | null): string | undefined {
  const raw = url?.trim();
  if (!raw) return undefined;

  const aliased = config.legacyAliases?.[raw] || raw;
  if (/^https?:\/\//i.test(aliased) || aliased.startsWith("data:")) {
    return aliased;
  }

  const oldStylePng = aliased.match(/^\/assets\/xiaoman\/styles\/([^/?#]+)\.png$/i);
  if (oldStylePng) return assetUrl(`styles/${oldStylePng[1]}.png`);

  const oldBase = aliased.match(/^\/assets\/xiaoman\/(avatar|avatar_small|onboarding)\.(jpg|png)$/i);
  if (oldBase) {
    const names: Record<string, string> = {
      avatar: "base.jpg",
      avatar_small: "base-small.jpg",
      onboarding: "onboarding.png",
    };
    return assetUrl(names[oldBase[1]] || oldBase[0]);
  }

  const oldEmotion = aliased.match(/^\/avatars\/(.+)$/i);
  if (oldEmotion) return assetUrl(`emotions/${oldEmotion[1]}`);

  const oldPlaceholder = aliased.match(/^\/styles\/(.+)$/i);
  if (oldPlaceholder) return assetUrl(`placeholders/${oldPlaceholder[1]}`);

  return aliased;
}

export const COMPANION_STYLES = config.styles.map((style) => style.id) as CompanionStyle[];

export const COMPANION_STYLE_OPTIONS: {
  id: CompanionStyle;
  label: string;
  desc: string;
}[] = config.styles.map(({ id, label, desc }) => ({ id, label, desc }));

export function normalizeCompanionStyle(style?: string | null): CompanionStyle {
  return (COMPANION_STYLES as readonly string[]).includes(style || "")
    ? (style as CompanionStyle)
    : config.defaultStyle;
}

export function getCompanionStyleConfig(style?: string | null): StyleAssetConfig {
  const id = normalizeCompanionStyle(style);
  return config.styles.find((item) => item.id === id) || config.styles[0];
}

export function stylePreviewUrl(style: string): string {
  return normalizeAvatarAssetUrl(getCompanionStyleConfig(style).preview) || config.fallbackPortrait;
}

export function stylePortraitUrl(style: string): string {
  return (
    normalizeAvatarAssetUrl(getCompanionStyleConfig(style).portrait) ||
    normalizeAvatarAssetUrl(config.fallbackPortrait) ||
    config.fallbackPortrait
  );
}

export function onboardingHeroUrl(style?: string | null): string {
  const styleConfig = getCompanionStyleConfig(style);
  return (
    normalizeAvatarAssetUrl(styleConfig.onboarding) ||
    normalizeAvatarAssetUrl(styleConfig.portrait) ||
    normalizeAvatarAssetUrl(config.onboarding.splash) ||
    config.onboarding.splash
  );
}

export function stylePortraitCandidates(style: string): string[] {
  const styleConfig = getCompanionStyleConfig(style);
  return [
    normalizeAvatarAssetUrl(styleConfig.portrait),
    normalizeAvatarAssetUrl(styleConfig.preview),
    normalizeAvatarAssetUrl(config.fallbackPortrait),
    normalizeAvatarAssetUrl(config.onboarding.splash),
  ].filter((url, index, urls): url is string => Boolean(url) && urls.indexOf(url) === index);
}

export function isEmotionPlaceholderUrl(url?: string | null): boolean {
  if (!url) return false;
  const normalized = normalizeAvatarAssetUrl(url);
  return (
    /^\/(?:avatars|styles)\//i.test(url) ||
    /\/avatar\/(?:emotions|placeholders)\//i.test(normalized || "")
  );
}

export function resolveCompanionPortraitUrl(
  style: string,
  dailyUrl?: string | null,
): string {
  const normalizedDailyUrl = normalizeAvatarAssetUrl(dailyUrl);
  if (normalizedDailyUrl && !isEmotionPlaceholderUrl(normalizedDailyUrl)) {
    return normalizedDailyUrl;
  }
  return stylePortraitUrl(style);
}

export function emotionAvatarUrl(emotion?: string): string | undefined {
  const key = emotion?.trim();
  if (!key) return undefined;
  return normalizeAvatarAssetUrl(config.emotions[key]);
}
