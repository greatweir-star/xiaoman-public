import { useCallback, useEffect, useMemo, useState } from "react";
import {
  emotionAvatarUrl,
  stylePortraitCandidates,
} from "../lib/companionAvatar";

function getEmotionOverlay(emotion: string | undefined): "happy" | "sad" | "surprised" | "shy" | "anxious" | null {
  if (!emotion) return null;
  if (["开心", "兴奋"].some((k) => emotion.includes(k))) return "happy";
  if (["难过", "委屈", "累"].some((k) => emotion.includes(k))) return "sad";
  if (["惊讶", "激动"].some((k) => emotion.includes(k))) return "surprised";
  if (emotion.includes("害羞")) return "shy";
  if (["焦虑", "烦"].some((k) => emotion.includes(k))) return "anxious";
  return null;
}

interface Props {
  emotion?: string;
  size?: "xs" | "sm" | "md" | "lg";
  onClick?: () => void;
  sleeping?: boolean;
  /** 每日/设定形象 URL，优先于默认 */
  srcOverride?: string;
  /** onboarding 画风，用于回退链 */
  style?: string;
  /** portrait=头部设定形象；emotion=消息气泡情绪图标 */
  mode?: "portrait" | "emotion";
  enlargeable?: boolean;
  title?: string;
}

export default function XiaomanAvatar({
  emotion,
  size = "md",
  onClick,
  sleeping = false,
  srcOverride,
  style = "fresh",
  mode = "portrait",
  enlargeable = false,
  title,
}: Props) {
  const sizeMap = {
    xs: { width: 32, height: 32 },
    sm: { width: 40, height: 40 },
    md: { width: 80, height: 80 },
    lg: { width: 120, height: 120 },
  };

  const s = sizeMap[size];
  const overlayType = getEmotionOverlay(emotion);

  const candidates = useMemo(() => {
    if (mode === "emotion") {
      const emo = emotionAvatarUrl(emotion);
      if (emo) return [emo, ...stylePortraitCandidates(style)];
      return stylePortraitCandidates(style);
    }
    if (srcOverride) return [srcOverride, ...stylePortraitCandidates(style)];
    return stylePortraitCandidates(style);
  }, [mode, emotion, srcOverride, style]);

  const [srcIndex, setSrcIndex] = useState(0);
  const imgSrc = candidates[Math.min(srcIndex, candidates.length - 1)];

  useEffect(() => {
    setSrcIndex(0);
  }, [candidates.join("|")]);

  const handleError = useCallback(() => {
    setSrcIndex((i) => (i + 1 < candidates.length ? i + 1 : i));
  }, [candidates.length]);

  const handleClick = () => {
    if (onClick) onClick();
  };

  return (
    <div
      className={`xiaoman-avatar${sleeping ? " sleeping" : ""}${enlargeable ? " enlargeable" : ""}`}
      style={{ width: s.width, height: s.height, flexShrink: 0, position: "relative" }}
      onClick={handleClick}
      title={title}
      role={enlargeable || onClick ? "button" : undefined}
      tabIndex={enlargeable || onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if ((enlargeable || onClick) && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      <img
        key={imgSrc}
        src={imgSrc}
        alt="小满"
        onError={handleError}
        style={{
          width: "100%",
          height: "100%",
          borderRadius: "50%",
          objectFit: "cover",
          transition: "opacity 200ms ease",
          opacity: sleeping ? 0.45 : 1,
          cursor: enlargeable || onClick ? "pointer" : undefined,
        }}
      />
      {mode === "emotion" && (
        <svg
          viewBox="0 0 100 100"
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
            transition: "opacity 200ms ease",
            opacity: overlayType ? 1 : 0,
          }}
        >
          {overlayType === "happy" && (
            <path d="M 35 65 Q 50 78 65 65" stroke="#5a3a3a" strokeWidth="4" fill="none" strokeLinecap="round" />
          )}
          {overlayType === "sad" && (
            <>
              <path d="M 32 42 Q 38 48 44 44" stroke="#5a3a3a" strokeWidth="3" fill="none" strokeLinecap="round" />
              <path d="M 56 44 Q 62 48 68 42" stroke="#5a3a3a" strokeWidth="3" fill="none" strokeLinecap="round" />
              <path d="M 40 70 Q 50 62 60 70" stroke="#5a3a3a" strokeWidth="3" fill="none" strokeLinecap="round" />
            </>
          )}
          {overlayType === "surprised" && (
            <>
              <circle cx="38" cy="48" r="5" fill="#5a3a3a" />
              <circle cx="62" cy="48" r="5" fill="#5a3a3a" />
              <path d="M 32 32 Q 38 28 44 32" stroke="#5a3a3a" strokeWidth="3" fill="none" strokeLinecap="round" />
              <path d="M 56 32 Q 62 28 68 32" stroke="#5a3a3a" strokeWidth="3" fill="none" strokeLinecap="round" />
              <circle cx="50" cy="68" r="4" fill="#5a3a3a" />
            </>
          )}
          {overlayType === "shy" && (
            <>
              <circle cx="28" cy="62" r="9" fill="#ffaaaa" opacity="0.35" />
              <circle cx="72" cy="62" r="9" fill="#ffaaaa" opacity="0.35" />
            </>
          )}
          {overlayType === "anxious" && (
            <>
              <path d="M 30 36 L 38 40 L 46 36" stroke="#5a3a3a" strokeWidth="3" fill="none" strokeLinecap="round" />
              <path d="M 54 36 L 62 40 L 70 36" stroke="#5a3a3a" strokeWidth="3" fill="none" strokeLinecap="round" />
            </>
          )}
        </svg>
      )}
    </div>
  );
}
