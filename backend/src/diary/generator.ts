export interface DailyState {
  date: string;
  mood_today: string;
  outfit_today: string;
  current_activity?: string;
  chat_turn_count: number;
  thoughts_today?: string[];
}

export interface Progress {
  login_streak: number;
}

export function generateDiary(daily: DailyState, progress: Progress): string {
  const parts: string[] = [];

  parts.push(`${daily.date} ${getWeekday(daily.date)}`);

  if (daily.mood_today) {
    parts.push(`今天${daily.mood_today}。`);
  }

  if (daily.outfit_today) {
    parts.push(`穿了${daily.outfit_today}。`);
  }

  if (daily.chat_turn_count > 0) {
    parts.push(`聊了${daily.chat_turn_count}轮。`);
  }

  if (progress.login_streak > 1) {
    parts.push(`连续${progress.login_streak}天见面了，开心。`);
  }

  return parts.join("");
}

function getWeekday(dateStr: string): string {
  const days = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  return days[new Date(dateStr).getDay()];
}
