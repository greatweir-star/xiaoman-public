import { useEffect, useState } from "react";
import {
  isEmotionPlaceholderUrl,
  resolveCompanionPortraitUrl,
} from "../lib/companionAvatar";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:18789";

export interface DailyAvatar {
  url: string;
  label: string;
  date: string;
  id: string;
}

export function useDailyAvatar(userId: string, style: string) {
  const [avatar, setAvatar] = useState<DailyAvatar | null>(null);

  useEffect(() => {
    if (!userId) return;
    const q = style ? `?style=${encodeURIComponent(style)}` : "";
    fetch(`${API_URL}/api/world/${userId}/daily-avatar${q}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d: DailyAvatar | null) => {
        if (!d) return;
        const url = isEmotionPlaceholderUrl(d.url)
          ? resolveCompanionPortraitUrl(style, null)
          : d.url;
        setAvatar({ ...d, url });
      })
      .catch(() => {});
  }, [userId, style]);

  return avatar;
}
