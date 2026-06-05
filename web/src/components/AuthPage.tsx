import { useEffect, useState } from "react";
import {
  fetchAuthHealth,
  loginAuth,
  registerAuth,
  type AuthTokenPair,
} from "../lib/backend";
import { onboardingHeroUrl } from "../lib/companionAvatar";

interface Props {
  onAuthenticated: (tokens: AuthTokenPair) => void;
  onLocalContinue: () => void;
}

function friendlyError(error: unknown): string {
  const message = error instanceof Error ? error.message : "";
  if (message.includes("invalid credentials")) return "邮箱或密码不正确";
  if (message.includes("email already registered")) return "这个邮箱已经注册过了";
  if (message.includes("email is invalid")) return "请输入有效邮箱";
  return "暂时无法完成登录，请稍后再试";
}

export default function AuthPage({ onAuthenticated, onLocalContinue }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [allowLocalMode, setAllowLocalMode] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAuthHealth()
      .then((health) => setAllowLocalMode(!health.auth_required))
      .catch(() => setAllowLocalMode(import.meta.env.DEV));
  }, []);

  const submit = async () => {
    setError("");
    const normalizedEmail = email.trim();
    if (!normalizedEmail || !password) {
      setError("请输入邮箱和密码");
      return;
    }
    if (mode === "register" && password.length < 8) {
      setError("密码至少需要 8 位");
      return;
    }
    if (mode === "register" && password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }
    setSubmitting(true);
    try {
      const tokens =
        mode === "login"
          ? await loginAuth(normalizedEmail, password)
          : await registerAuth(normalizedEmail, password);
      onAuthenticated(tokens);
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const switchMode = () => {
    setMode((current) => (current === "login" ? "register" : "login"));
    setConfirmPassword("");
    setError("");
  };

  return (
    <main className="auth-page">
      <section className="auth-card">
        <img src={onboardingHeroUrl("fresh")} alt="小满" className="auth-hero" />
        <p className="auth-kicker">小满 SaaS</p>
        <h1>{mode === "login" ? "欢迎回来" : "创建你的账号"}</h1>
        <p className="auth-hint">
          {mode === "login" ? "登录后继续和小满聊天" : "用邮箱保存属于你的陪伴记录"}
        </p>

        <div className="auth-fields">
          <input
            type="email"
            autoComplete="email"
            placeholder="邮箱"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <input
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            placeholder={mode === "login" ? "密码" : "密码（至少 8 位）"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && void submit()}
          />
          {mode === "register" && (
            <input
              type="password"
              autoComplete="new-password"
              placeholder="再次输入密码"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && void submit()}
            />
          )}
        </div>

        {error && <p className="auth-error">{error}</p>}

        <button type="button" className="auth-primary-btn" disabled={submitting} onClick={() => void submit()}>
          {submitting ? "请稍候…" : mode === "login" ? "登录" : "注册并继续"}
        </button>
        <button type="button" className="auth-switch-btn" onClick={switchMode}>
          {mode === "login" ? "还没有账号？注册" : "已有账号？登录"}
        </button>

        {allowLocalMode && (
          <button type="button" className="auth-local-btn" onClick={onLocalContinue}>
            继续本地体验
          </button>
        )}
      </section>
    </main>
  );
}
