import { useState, type FormEvent } from "react";
import {
  loginAccount,
  logoutAccount,
  claimGuestData,
  getGuestId,
  registerAccount,
  setAuthTokens,
  type AuthTokenPair,
} from "../lib/backend";

interface AuthPanelProps {
  email: string;
  onAuthenticated: (tokens: AuthTokenPair) => void;
  onLoggedOut: () => void;
  onFinished?: () => void;
  presentation?: "card" | "sheet";
}

type SyncState = "idle" | "syncing" | "saved" | "error";

export default function AuthPanel({
  email,
  onAuthenticated,
  onLoggedOut,
  onFinished,
  presentation = "card",
}: AuthPanelProps) {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [inputEmail, setInputEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [syncState, setSyncState] = useState<SyncState>("idle");

  const syncGuestProgress = async () => {
    const guestId = getGuestId();
    if (!guestId) {
      setMessage("此设备没有待同步的游客进度");
      return;
    }
    setSyncState("syncing");
    try {
      const claimed = await claimGuestData(guestId);
      setMessage(claimed ? "游客进度已保存" : "此设备没有待同步的游客进度");
      setSyncState(claimed ? "saved" : "idle");
    } catch (error) {
      setMessage(error instanceof Error ? `${error.message}，本机数据仍保留，可重试` : "游客进度同步失败，本机数据仍保留，可重试");
      setSyncState("error");
    }
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setMessage("");
    if (!inputEmail || password.length < 8) {
      setMessage("请输入邮箱和至少 8 位密码");
      return;
    }
    if (mode === "register" && password !== confirmPassword) {
      setMessage("两次输入的密码不一致");
      return;
    }
    setSubmitting(true);
    try {
      const guestId = getGuestId();
      const tokens = mode === "register"
        ? await registerAccount(inputEmail, password)
        : await loginAccount(inputEmail, password);
      setAuthTokens(tokens);
      onAuthenticated(tokens);
      setSyncState(guestId ? "syncing" : "idle");
      const claimed = guestId ? await claimGuestData(guestId) : null;
      setPassword("");
      setConfirmPassword("");
      setMessage(claimed ? "已登录，游客进度已保存" : "已登录，此设备没有待同步的游客进度");
      setSyncState(claimed ? "saved" : "idle");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "登录失败，请稍后重试");
      setSyncState("error");
    } finally {
      setSubmitting(false);
    }
  };

  const logout = async () => {
    if (!window.confirm("退出登录后，本机游客数据仍会保留。确定退出吗？")) return;
    await logoutAccount();
    onLoggedOut();
    setMessage("已退出登录");
  };

  if (syncState === "syncing") {
    return (
      <div className={`auth-panel auth-panel-${presentation}`} aria-live="polite">
        <p className="soft-eyebrow">SYNCING</p>
        <h3>正在保存你们的故事</h3>
        <p className="settings-secrets-hint">
          不用担心，本机记录会保留。同步完成后，你可以在其他设备登录回来。
        </p>
        <div className="auth-progress" aria-hidden="true">
          <span />
        </div>
        <ul className="auth-sync-steps">
          <li className="is-complete">确认本机游客进度</li>
          <li>保存聊天与记忆</li>
          <li>整理成长记录</li>
        </ul>
      </div>
    );
  }

  if (syncState === "saved") {
    return (
      <div className={`auth-panel auth-panel-${presentation}`} aria-live="polite">
        <p className="soft-eyebrow">SAVED</p>
        <h3>保存好了</h3>
        <p className="settings-secrets-hint">
          下次换个设备登录，小满也会记得你们聊过的事。
        </p>
        {onFinished ? (
          <button type="button" className="auth-primary-btn" onClick={onFinished}>
            回去找小满
          </button>
        ) : null}
      </div>
    );
  }

  if (email) {
    return (
      <div className={`auth-panel auth-panel-${presentation}`}>
        <p className="soft-eyebrow">ACCOUNT</p>
        <h3>账号与同步</h3>
        <p className="settings-secrets-hint">已登录：{email}</p>
        {getGuestId() && (
          <button type="button" className="auth-primary-btn" onClick={syncGuestProgress}>
            重试保存游客进度
          </button>
        )}
        <button type="button" className="auth-secondary-btn" onClick={logout}>退出登录</button>
        {message && <p className="auth-message" aria-live="polite">{message}</p>}
      </div>
    );
  }

  return (
    <div className={`auth-panel auth-panel-${presentation}`}>
      <p className="soft-eyebrow">ACCOUNT</p>
      <h3>保存你和小满的关系</h3>
      <p className="settings-secrets-hint">注册或登录后，可以在其他设备继续。</p>
      <div className="auth-tabs" role="tablist" aria-label="账号方式">
        <button type="button" role="tab" aria-selected={mode === "register"} className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>注册</button>
        <button type="button" role="tab" aria-selected={mode === "login"} className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>登录</button>
      </div>
      <form className="auth-form" onSubmit={submit}>
        <label htmlFor="auth-email">邮箱</label>
        <input
          id="auth-email"
          name="email"
          type="email"
          autoComplete="email"
          spellCheck={false}
          value={inputEmail}
          onChange={(event) => setInputEmail(event.target.value)}
          placeholder="例如 name@example.com…"
        />
        <label htmlFor="auth-password">密码</label>
        <input
          id="auth-password"
          name="password"
          type="password"
          autoComplete={mode === "register" ? "new-password" : "current-password"}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="至少 8 位…"
        />
        {mode === "register" && (
          <>
            <label htmlFor="auth-confirm-password">确认密码</label>
            <input
              id="auth-confirm-password"
              name="confirm-password"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="再次输入密码…"
            />
          </>
        )}
        <button type="submit" className="auth-primary-btn" disabled={submitting}>
          {submitting ? "处理中…" : mode === "register" ? "注册并保存进度" : "登录并恢复进度"}
        </button>
      </form>
      <p className="auth-privacy-note">
        继续即表示你了解：小满会保存你主动告诉她的内容，你可以随时查看、导出或删除。
      </p>
      {message && <p className="auth-message" aria-live="polite">{message}</p>}
    </div>
  );
}
