import { apiJson } from "../lib/backend";
import { useEffect, useState } from "react";
import {
  resolveCompanionPortraitUrl,
} from "../lib/companionAvatar";

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
    apiJson<DailyAvatar | null>(`/api/world/${userId}/daily-avatar${q}`, null).then((d) => {
      if (!d) return;
      setAvatar({ ...d, url: resolveCompanionPortraitUrl(style, d.url) });
    });
  }, [userId, style]);

  return avatar;
}
