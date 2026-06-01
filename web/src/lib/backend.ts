const DEV_BACKEND_PORT = "18789";
const ACCESS_TOKEN_KEY = "xiaoman_access_token";
const REFRESH_TOKEN_KEY = "xiaoman_refresh_token";
const AUTH_EMAIL_KEY = "xiaoman_auth_email";
const ACTIVE_USER_ID_KEY = "xiaoman_user_id";
const GUEST_ID_KEY = "xiaoman_guest_id";

export interface AuthTokenPair {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: {
    id: string;
    tenant_id: string;
    email: string;
    status: string;
  };
}

export interface GuestClaimResult {
  status: "completed";
  guest_id: string;
  user_id: string;
  archive_path: string;
}

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function isLocalHost(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

function isLocalViteDev(): boolean {
  if (!isBrowser()) return false;
  const { hostname, port } = window.location;
  return isLocalHost(hostname) && port !== "" && port !== "3000" && port !== "80";
}

function withJsonBody(init: RequestInit, body: unknown): RequestInit {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return {
    ...init,
    method: init.method || "POST",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  };
}

function withAuth(init: RequestInit = {}): RequestInit {
  const headers = new Headers(init.headers);
  const accessToken = getAccessToken();
  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  return { ...init, headers };
}

export function getAccessToken(): string {
  return isBrowser() ? localStorage.getItem(ACCESS_TOKEN_KEY) || "" : "";
}

export function getRefreshToken(): string {
  return isBrowser() ? localStorage.getItem(REFRESH_TOKEN_KEY) || "" : "";
}

export function setAuthTokens(tokens: AuthTokenPair): void {
  if (!isBrowser()) return;
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  localStorage.setItem(ACTIVE_USER_ID_KEY, tokens.user.id);
  localStorage.setItem(AUTH_EMAIL_KEY, tokens.user.email);
}

export function ensureGuestId(): string {
  if (!isBrowser()) return "";
  const existing = localStorage.getItem(GUEST_ID_KEY);
  if (existing) return existing;
  const activeUserId = localStorage.getItem(ACTIVE_USER_ID_KEY);
  const guestId = !getAccessToken() && activeUserId ? activeUserId : crypto.randomUUID();
  localStorage.setItem(GUEST_ID_KEY, guestId);
  localStorage.setItem(ACTIVE_USER_ID_KEY, guestId);
  return guestId;
}

export function createNewGuestId(): string {
  if (!isBrowser()) return "";
  const guestId = crypto.randomUUID();
  localStorage.setItem(GUEST_ID_KEY, guestId);
  localStorage.setItem(ACTIVE_USER_ID_KEY, guestId);
  return guestId;
}

export function getGuestId(): string {
  return isBrowser() ? localStorage.getItem(GUEST_ID_KEY) || "" : "";
}

export function completeGuestClaim(userId: string): void {
  if (!isBrowser()) return;
  localStorage.removeItem(GUEST_ID_KEY);
  localStorage.setItem(ACTIVE_USER_ID_KEY, userId);
}

export function clearAuthTokens(): void {
  if (!isBrowser()) return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(AUTH_EMAIL_KEY);
}

export function getAuthEmail(): string {
  return isBrowser() ? localStorage.getItem(AUTH_EMAIL_KEY) || "" : "";
}

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_URL;
  if (configured) return configured.replace(/\/$/, "");
  if (!isBrowser()) return `http://localhost:${DEV_BACKEND_PORT}`;
  if (isLocalViteDev()) return `http://localhost:${DEV_BACKEND_PORT}`;
  return window.location.origin;
}

export function getGatewayUrl(): string {
  const configured = import.meta.env.VITE_GATEWAY_URL;
  if (configured) return configured;
  if (!isBrowser()) return `ws://localhost:${DEV_BACKEND_PORT}/ws`;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  if (isLocalViteDev()) return `${protocol}//localhost:${DEV_BACKEND_PORT}/ws`;
  return `${protocol}//${window.location.host}/ws`;
}

export function apiUrl(path: string): string {
  const lowerPath = path.toLowerCase();
  if (lowerPath.startsWith("http://") || lowerPath.startsWith("https://")) return path;
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${getApiBaseUrl()}${normalized}`;
}

async function rawPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(apiUrl(path), withJsonBody({}, body));
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "请求失败");
  }
  return response.json() as Promise<T>;
}

export async function refreshAuthTokens(): Promise<AuthTokenPair | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  try {
    const tokens = await rawPost<AuthTokenPair>("/api/auth/refresh", { refresh_token: refreshToken });
    setAuthTokens(tokens);
    return tokens;
  } catch {
    clearAuthTokens();
    return null;
  }
}

export function registerAccount(email: string, password: string): Promise<AuthTokenPair> {
  return rawPost<AuthTokenPair>("/api/auth/register", { email, password });
}

export function loginAccount(email: string, password: string): Promise<AuthTokenPair> {
  return rawPost<AuthTokenPair>("/api/auth/login", { email, password });
}

export async function logoutAccount(): Promise<void> {
  const refreshToken = getRefreshToken();
  if (refreshToken) {
    await rawPost("/api/auth/logout", { refresh_token: refreshToken }).catch(() => undefined);
  }
  clearAuthTokens();
}

export async function claimGuestData(guestId: string): Promise<GuestClaimResult | null> {
  if (!guestId) return null;
  try {
    const token = await rawPost<{ claim_token: string }>("/api/auth/guest-claim-token", { guest_id: guestId });
    const response = await apiFetch("/api/auth/claim-guest", withJsonBody({}, {
      guest_id: guestId,
      claim_token: token.claim_token,
    }));
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || "游客进度同步失败");
    }
    const result = await response.json() as GuestClaimResult;
    completeGuestClaim(result.user_id);
    return result;
  } catch (error) {
    if (error instanceof Error && error.message === "guest data not found") return null;
    throw error;
  }
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  let response = await fetch(apiUrl(path), withAuth(init));
  if (response.status !== 401 || path.startsWith("/api/auth/")) return response;
  const tokens = await refreshAuthTokens();
  if (!tokens) return response;
  response = await fetch(apiUrl(path), withAuth(init));
  return response;
}

export async function apiJson<T>(path: string, fallback: T, init?: RequestInit): Promise<T> {
  try {
    const response = await apiFetch(path, init);
    if (!response.ok) return fallback;
    const text = await response.text();
    if (!text) return fallback;
    return JSON.parse(text) as T;
  } catch {
    return fallback;
  }
}

export function apiPostJson<T>(path: string, body: unknown, fallback: T, init: RequestInit = {}): Promise<T> {
  return apiJson<T>(path, fallback, withJsonBody(init, body));
}
