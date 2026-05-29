export interface UserIdentity {
  name: string;
  xiaoman_name: string;
  gender: "female" | "male";
  grade: string;
  style_preference: string;
}

export interface UserWorkflow {
  dailyRhythm: string[];
  studyHabits: string[];
  emotionalPatterns: Array<{
    trigger: string;
    response: string;
    frequency: number;
  }>;
  last_emotion: string;
}

export interface UserVoice {
  catchphrases: string[];
  typingStyle: string;
  favoriteMemes: string[];
}

export interface UserInstruction {
  explicitRules: string[];
  taboos: string[];
  preferences: string[];
}

export interface UserMemory {
  identity: UserIdentity;
  workflow: UserWorkflow;
  voice: UserVoice;
  instruction: UserInstruction;
}

export interface DailyState {
  date: string;
  mood_today: string;
  outfit_today: string;
  current_activity: string;
  chat_turn_count: number;
  thoughts_today: string[];
}

export interface Progress {
  intimacy_level: number;
  intimacy_points: number;
  total_dialogue_turns: number;
  total_usage_days: number;
  login_streak: number;
  unlocked_skills: string[];
  last_login_date: string;
}
