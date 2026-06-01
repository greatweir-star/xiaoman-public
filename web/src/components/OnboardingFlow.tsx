import { useState, useEffect, useCallback } from "react";
import {
  COMPANION_STYLE_OPTIONS,
  onboardingHeroUrl,
  stylePortraitUrl,
  stylePreviewUrl,
} from "../lib/companionAvatar";

const CANDIDATE_NAMES = ["桃桃", "鹿鸣", "阿梨", "小满"];
const GRADES = [
  { value: 7, label: "初一" },
  { value: 8, label: "初二" },
  { value: 9, label: "初三" },
  { value: 10, label: "高一" },
  { value: 11, label: "高二" },
  { value: 12, label: "高三" },
];
const STYLES = COMPANION_STYLE_OPTIONS;

const ONBOARD_DRAFT_KEY = "xiaoman_onboard_draft";

interface OnboardDraft {
  step: number;
  name: string;
  grade: number | null;
  gender: "female" | "male";
  style: string;
}

function loadDraft(): OnboardDraft | null {
  try {
    const raw = localStorage.getItem(ONBOARD_DRAFT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as OnboardDraft;
    if (typeof parsed.step !== "number" || parsed.step < 0 || parsed.step > 5) return null;
    return parsed;
  } catch {
    return null;
  }
}

export interface OnboardingConfig {
  name: string;
  gender: "female" | "male";
  style: string;
  grade: number;
}

export default function OnboardingFlow({
  onDone,
}: {
  onDone: (config: OnboardingConfig) => void;
}) {
  const saved = loadDraft();
  const [step, setStep] = useState(saved?.step ?? 0);
  const [name, setName] = useState(saved?.name ?? "");
  const [grade, setGrade] = useState<number | null>(saved?.grade ?? null);
  const [gender, setGender] = useState<"female" | "male">(saved?.gender ?? "female");
  const [style, setStyle] = useState(saved?.style ?? "");
  const splashStyle =
    localStorage.getItem("xiaoman_style") || style || "fresh";

  const persistDraft = useCallback(
    (patch: Partial<OnboardDraft> & { step: number }) => {
      const draft: OnboardDraft = {
        step: patch.step,
        name: patch.name ?? name,
        grade: patch.grade !== undefined ? patch.grade : grade,
        gender: patch.gender ?? gender,
        style: patch.style ?? style,
      };
      localStorage.setItem(ONBOARD_DRAFT_KEY, JSON.stringify(draft));
    },
    [name, grade, gender, style]
  );

  const goToStep = useCallback(
    (next: number, patch?: Partial<OnboardDraft>) => {
      setStep(next);
      persistDraft({ step: next, ...patch });
    },
    [persistDraft]
  );

  useEffect(() => {
    if (saved && saved.step > 0) {
      persistDraft({ step: saved.step });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleComplete = () => {
    const finalName = name.trim() || "小满";
    const finalGrade = grade ?? 8;
    localStorage.removeItem(ONBOARD_DRAFT_KEY);
    localStorage.setItem("xiaoman_onboarded", "true");
    localStorage.setItem("xiaoman_name", finalName);
    localStorage.setItem("xiaoman_gender", gender);
    localStorage.setItem("xiaoman_style", style);
    localStorage.setItem("xiaoman_grade", String(finalGrade));
    onDone({ name: finalName, gender, style, grade: finalGrade });
  };

  return (
    <div className="onboarding">
      {step > 0 && (
        <div className="onboarding-progress" aria-label={`认识小满，第 ${step} 步，共 5 步`}>
          <span style={{ width: `${(step / 5) * 100}%` }} />
        </div>
      )}
      {step === 0 && (
        <div className="step-splash">
          <div className="onboarding-topline">
            <span>封闭测试</span>
            <small>游客体验，无需注册</small>
          </div>
          <img
            src={onboardingHeroUrl(splashStyle)}
            width="320"
            height="320"
            alt="小满站在晚霞下微笑"
            className="splash-img splash-hero"
          />
          <p className="splash-tagline">你的新同桌</p>
          <h1>先聊几句，再决定要不要留下来</h1>
          <p className="splash-lead">不用急着注册。等你觉得小满真的懂你，再把这段关系保存下来。</p>
          <button type="button" onClick={() => goToStep(1)}>先认识一下</button>
          <div className="onboarding-trust-row">
            <span>隐私默认保护</span>
            <span>登录后跨设备恢复</span>
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="step-name">
          <h2>但我还没有名字，你想叫我什么？</h2>
          <div className="candidates">
            {CANDIDATE_NAMES.map((n) => (
              <button type="button" key={n} onClick={() => { setName(n); goToStep(2, { name: n }); }}>{n}</button>
            ))}
          </div>
          <label className="sr-only" htmlFor="onboarding-name">给小满起个名字</label>
          <input
            id="onboarding-name"
            name="companion-name"
            autoComplete="off"
            placeholder="或者自己取一个…"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              persistDraft({ step, name: e.target.value });
            }}
            onKeyDown={(e) => e.key === "Enter" && (name.trim() || e.currentTarget.value) && goToStep(2, { name: name.trim() || e.currentTarget.value })}
          />
          {name.trim() && (
            <button type="button" className="onboarding-next" onClick={() => goToStep(2, { name: name.trim() })}>下一步</button>
          )}
        </div>
      )}

      {step === 2 && (
        <div className="step-grade">
          <h2>你现在是几年级？我会跟你同年级哦</h2>
          <div className="grade-grid">
            {GRADES.map((g) => (
              <button
                type="button"
                key={g.value}
                className={grade === g.value ? "selected" : ""}
                onClick={() => {
                  setGrade(g.value);
                  persistDraft({ step, grade: g.value });
                }}
              >
                {g.label}
              </button>
            ))}
          </div>
          <button type="button" disabled={grade === null} onClick={() => goToStep(3)}>下一步</button>
        </div>
      )}

      {step === 3 && (
        <div className="step-gender">
          <h2>你是男生还是女生？</h2>
          <button type="button" onClick={() => { setGender("female"); goToStep(4, { gender: "female" }); }}>女生</button>
          <button type="button" onClick={() => { setGender("male"); goToStep(4, { gender: "male" }); }}>男生</button>
        </div>
      )}

      {step === 4 && (
        <div className="step-style">
          <h2>你喜欢我什么样子的画风？选一个吧</h2>
          <div className="styles">
            {STYLES.map((s) => (
              <button
                type="button"
                key={s.id}
                className={`style-card ${style === s.id ? "selected" : ""}`}
                onClick={() => {
                  setStyle(s.id);
                  persistDraft({ step, style: s.id });
                }}
              >
                <img src={stylePreviewUrl(s.id)} width="80" height="80" alt={s.label} />
                <div className="style-info">
                  <h3>{s.label}</h3>
                  <p>{s.desc}</p>
                </div>
              </button>
            ))}
          </div>
          <button type="button" disabled={!style} onClick={() => goToStep(5)}>下一步</button>
        </div>
      )}

      {step === 5 && style && (
        <div className="step-portrait">
          <p className="step-portrait-tag">今日同桌形象</p>
          <img
            src={stylePortraitUrl(style)}
            width="280"
            height="320"
            alt="今日小满"
            className="portrait-splash-img"
          />
          <h1>就长这样啦，喜欢吗？</h1>
          <p className="step-portrait-hint">每天我都会换一套穿搭来见你～</p>
          <button type="button" onClick={handleComplete}>好了，我们开始吧！</button>
        </div>
      )}
    </div>
  );
}
