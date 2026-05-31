import { apiFetch, apiJson } from "../lib/backend";
import { useState, useEffect } from "react";
import {
  COMPANION_STYLE_OPTIONS,
  stylePreviewUrl,
  type CompanionStyle,
} from "../lib/companionAvatar";

interface SettingsPageProps {
  userId: string;
  style: string;
  onStyleChange: (style: CompanionStyle) => void;
  onNavigate: (view: "xiaoman-world" | "user-world") => void;
}

interface SecretItem {
  id?: string;
  content?: string;
  level?: string;
  timestamp?: string;
}

interface ParentalConfig {
  enabled: boolean;
  password: string;
  daily_limit_minutes: number;
  session_limit_minutes: number;
  night_start: string;
  night_end: string;
  crisis_resources_enabled: boolean;
}

interface UsageStats {
  daily_used: number;
  daily_remaining: number;
  session_used: number;
  session_remaining: number;
  night_locked: boolean;
}

const defaultConfig: ParentalConfig = {
  enabled: false,
  password: "",
  daily_limit_minutes: 60,
  session_limit_minutes: 30,
  night_start: "23:00",
  night_end: "06:00",
  crisis_resources_enabled: true,
};

export default function SettingsPage({
  userId,
  style,
  onStyleChange,
  onNavigate,
}: SettingsPageProps) {
  const [secrets, setSecrets] = useState<SecretItem[]>([]);
  const [revealed, setRevealed] = useState(false);
  const [loadingSecrets, setLoadingSecrets] = useState(false);
  const [savingStyle, setSavingStyle] = useState(false);
  const [styleSaved, setStyleSaved] = useState(false);

  const [parentalPanel, setParentalPanel] = useState(false);
  const [cfg, setCfg] = useState<ParentalConfig>(defaultConfig);
  const [passwordInput, setPasswordInput] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [savingParental, setSavingParental] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [usage, setUsage] = useState<UsageStats | null>(null);

  const loadSecrets = (reveal: boolean) => {
    setLoadingSecrets(true);
    apiJson<{ secrets?: SecretItem[] }>(`/api/memory/${userId}/secrets?reveal=${reveal}`, { secrets: [] })
      .then((d) => setSecrets(d.secrets || []))
      .finally(() => setLoadingSecrets(false));
  };

  useEffect(() => {
    loadSecrets(false);
  }, [userId]);

  const fetchParentalConfig = () => {
    apiJson<Partial<ParentalConfig> | null>(`/api/world/${userId}/parental`, null).then((d) => {
      if (d) setCfg({ ...defaultConfig, ...d });
    });
  };

  const fetchUsage = () => {
    apiJson<UsageStats | null>(`/api/world/${userId}/usage`, null).then((d) => {
      if (d) setUsage(d);
    });
  };

  useEffect(() => {
    if (parentalPanel) {
      fetchParentalConfig();
      fetchUsage();
    }
  }, [parentalPanel, userId]);

  const handleReveal = () => {
    if (
      !window.confirm(
        "查看秘密内容需要你的确认。这些内容仅保存在本地加密存储中，确定要显示吗？"
      )
    ) {
      return;
    }
    setRevealed(true);
    loadSecrets(true);
  };

  const handlePickStyle = async (next: CompanionStyle) => {
    if (next === style) return;
    setSavingStyle(true);
    setStyleSaved(false);
    try {
      const res = await apiFetch(`/api/world/${userId}/identity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ style: next }),
      });
      if (res.ok) {
        onStyleChange(next);
        setStyleSaved(true);
        window.setTimeout(() => setStyleSaved(false), 2000);
      }
    } finally {
      setSavingStyle(false);
    }
  };

  const handleSaveParental = async () => {
    setSaveMsg("");
    if (cfg.enabled) {
      if (!/^\d{4}$/.test(passwordInput)) {
        setSaveMsg("密码必须是 4 位数字");
        return;
      }
      if (!cfg.password && passwordInput !== passwordConfirm) {
        setSaveMsg("两次密码不一致");
        return;
      }
    }
    setSavingParental(true);
    try {
      const body: ParentalConfig = {
        ...cfg,
        password: cfg.password || passwordInput,
      };
      const res = await apiFetch(`/api/world/${userId}/parental`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config: body, password: passwordInput }),
      });
      const d = await res.json();
      if (d.success) {
        setSaveMsg("保存成功");
        setPasswordInput("");
        setPasswordConfirm("");
        fetchParentalConfig();
        fetchUsage();
      } else {
        setSaveMsg("密码验证失败");
      }
    } catch {
      setSaveMsg("保存失败，请检查网络");
    } finally {
      setSavingParental(false);
    }
  };

  if (parentalPanel) {
    return (
      <div className="settings-page">
        <div className="sub-page-header">
          <button type="button" className="sub-page-back" onClick={() => setParentalPanel(false)}>
            ‹ 返回
          </button>
          <h2>家长模式</h2>
          <span />
        </div>
        <div className="parental-panel">
          <div className="settings-row">
            <label>启用家长模式</label>
            <input
              type="checkbox"
              checked={cfg.enabled}
              onChange={(e) => setCfg({ ...cfg, enabled: e.target.checked })}
            />
          </div>

          <div className="settings-row">
            <label>{cfg.password ? "验证密码" : "设置 4 位密码"}</label>
            <input
              type="password"
              inputMode="numeric"
              maxLength={4}
              value={passwordInput}
              onChange={(e) => setPasswordInput(e.target.value.replace(/\D/g, ""))}
              placeholder="••••"
              className="parental-input"
            />
          </div>
          {!cfg.password && (
            <div className="settings-row">
              <label>确认密码</label>
              <input
                type="password"
                inputMode="numeric"
                maxLength={4}
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value.replace(/\D/g, ""))}
                placeholder="••••"
                className="parental-input"
              />
            </div>
          )}

          <div className="settings-row">
            <label>每日最大时长（分钟）</label>
            <div className="range-wrap">
              <input
                type="range"
                min={15}
                max={180}
                step={5}
                value={cfg.daily_limit_minutes}
                onChange={(e) => setCfg({ ...cfg, daily_limit_minutes: Number(e.target.value) })}
              />
              <span className="range-value">{cfg.daily_limit_minutes}</span>
            </div>
          </div>

          <div className="settings-row">
            <label>单次连续上限（分钟）</label>
            <div className="range-wrap">
              <input
                type="range"
                min={10}
                max={60}
                step={5}
                value={cfg.session_limit_minutes}
                onChange={(e) => setCfg({ ...cfg, session_limit_minutes: Number(e.target.value) })}
              />
              <span className="range-value">{cfg.session_limit_minutes}</span>
            </div>
          </div>

          <div className="settings-row">
            <label>夜间禁用时段</label>
            <div className="time-range">
              <input
                type="time"
                value={cfg.night_start}
                onChange={(e) => setCfg({ ...cfg, night_start: e.target.value })}
              />
              <span>至</span>
              <input
                type="time"
                value={cfg.night_end}
                onChange={(e) => setCfg({ ...cfg, night_end: e.target.value })}
              />
            </div>
          </div>

          <div className="settings-row">
            <label>敏感话题资源卡片</label>
            <input
              type="checkbox"
              checked={cfg.crisis_resources_enabled}
              onChange={(e) => setCfg({ ...cfg, crisis_resources_enabled: e.target.checked })}
            />
          </div>

          <button
            type="button"
            className="parental-save-btn"
            onClick={handleSaveParental}
            disabled={savingParental}
          >
            {savingParental ? "保存中…" : "保存"}
          </button>
          {saveMsg && <p className="parental-save-msg">{saveMsg}</p>}

          {usage && (
            <div className="parental-usage">
              <p>
                今日已使用 <strong>{usage.daily_used}</strong> 分钟 / 剩余{" "}
                <strong>{usage.daily_remaining}</strong> 分钟
              </p>
              <p className="parental-usage-sub">
                连续使用 {usage.session_used} 分钟 / 剩余 {usage.session_remaining} 分钟
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="settings-page">
      <h2 className="settings-title">设置</h2>

      <div className="settings-style-section">
        <h3 className="settings-style-heading">小满画风</h3>
        <p className="settings-secrets-hint">
          更换后聊天与 Life 页头像会同步更新（每日轮换仍按画风）
        </p>
        <div className="styles settings-styles">
          {COMPANION_STYLE_OPTIONS.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`style-card ${style === s.id ? "selected" : ""}`}
              disabled={savingStyle}
              onClick={() => handlePickStyle(s.id)}
            >
              <img src={stylePreviewUrl(s.id)} alt={s.label} />
              <div className="style-info">
                <h3>{s.label}</h3>
                <p>{s.desc}</p>
              </div>
            </button>
          ))}
        </div>
        {savingStyle && (
          <p className="settings-secrets-hint">保存中…</p>
        )}
        {styleSaved && (
          <p className="settings-style-saved">已更新画风</p>
        )}
      </div>

      <div className="settings-menu">
        <div className="settings-menu-item" onClick={() => onNavigate("xiaoman-world")}>
          <div className="settings-menu-left">
            <span className="settings-menu-icon" style={{ background: "#e3f2fd", color: "#1976d2" }}>满</span>
            <div>
              <div className="settings-menu-name">小满的世界</div>
              <div className="settings-menu-desc">她的身份、生活、日程、情绪</div>
            </div>
          </div>
          <span className="settings-menu-arrow">›</span>
        </div>

        <div className="settings-menu-item" onClick={() => onNavigate("user-world")}>
          <div className="settings-menu-left">
            <span className="settings-menu-icon" style={{ background: "#f3e5f5", color: "#7b1fa2" }}>你</span>
            <div>
              <div className="settings-menu-name">你的世界</div>
              <div className="settings-menu-desc">你的身份、情绪、画像</div>
            </div>
          </div>
          <span className="settings-menu-arrow">›</span>
        </div>

        <div className="settings-menu-item" onClick={() => setParentalPanel(true)}>
          <div className="settings-menu-left">
            <span className="settings-menu-icon" style={{ background: "#fff3e0", color: "#e65100" }}>家</span>
            <div>
              <div className="settings-menu-name">家长模式</div>
              <div className="settings-menu-desc">使用时长、夜间锁、密码保护</div>
            </div>
          </div>
          <span className="settings-menu-arrow">›</span>
        </div>
      </div>

      <div className="settings-secrets-section">
        <div className="settings-secrets-header">
          <h3>小满知道的秘密</h3>
          {!revealed && (
            <button type="button" className="memory-btn" onClick={handleReveal}>
              查看内容
            </button>
          )}
        </div>
        {loadingSecrets && <p className="settings-secrets-hint">加载中…</p>}
        {!loadingSecrets && secrets.length === 0 && (
          <p className="settings-secrets-hint">还没有记录秘密</p>
        )}
        <ul className="settings-secrets-list">
          {secrets.map((s, i) => (
            <li key={s.id || i} className="settings-secret-item">
              <span className="settings-secret-content">{s.content}</span>
              {s.timestamp && (
                <span className="settings-secret-time">{s.timestamp.slice(0, 10)}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
