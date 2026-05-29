export interface Progress {
  total_dialogue_turns: number;
  total_usage_days: number;
  login_streak: number;
  last_login_date: string;
}

export function calculateLevel(progress: Progress): number {
  if (progress.total_dialogue_turns >= 200 || progress.total_usage_days >= 30) return 5;
  if (progress.total_dialogue_turns >= 100 || progress.total_usage_days >= 14) return 4;
  if (progress.total_dialogue_turns >= 50 || progress.total_usage_days >= 7) return 3;
  if (progress.total_dialogue_turns >= 20 || progress.total_usage_days >= 3) return 2;
  return 1;
}

export function getLevelName(level: number): string {
  const names = ["", "新同桌", "饭搭子", "树洞", "闺蜜/老铁", "灵魂搭档"];
  return names[level] || "新同桌";
}

export function getLevelProgress(progress: Progress): { current: number; total: number } {
  const level = calculateLevel(progress);
  const thresholds = [0, 20, 50, 100, 200];
  const currentThreshold = thresholds[level - 1] || 0;
  const nextThreshold = thresholds[level] || 200;
  const current = Math.min(progress.total_dialogue_turns, nextThreshold);
  return { current: current - currentThreshold, total: nextThreshold - currentThreshold };
}

export function updateProgress(progress: Progress): Progress {
  const today = new Date().toISOString().split("T")[0];
  const updated = { ...progress };

  updated.total_dialogue_turns += 1;

  if (updated.last_login_date === today) {
    // 同一天，不增加天数
  } else if (updated.last_login_date) {
    const last = new Date(updated.last_login_date);
    const now = new Date(today);
    const diff = (now.getTime() - last.getTime()) / (1000 * 60 * 60 * 24);
    if (diff === 1) {
      updated.login_streak += 1;
    } else {
      updated.login_streak = 1;
    }
    updated.total_usage_days += 1;
  } else {
    updated.login_streak = 1;
    updated.total_usage_days = 1;
  }

  updated.last_login_date = today;
  return updated;
}
