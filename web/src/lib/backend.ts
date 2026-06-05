const DEV_BACKEND_PORT = "18789";
const ACCESS_TOKEN_KEY = "xiaoman_access_token";
const REFRESH_TOKEN_KEY = "xiaoman_refresh_token";

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

export interface AuthHealth {
  status: string;
  auth_required: boolean;
}

let refreshPromise: Promise<AuthTokenPair | null> | null = null;

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
  localStorage.setItem("xiaoman_user_id", tokens.user.id);
}

export function clearAuthTokens(): void {
  if (!isBrowser()) return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function responseError(response: Response): Promise<Error> {
  try {
    const payload = await response.json();
    if (typeof payload?.detail === "string") {
      return new Error(payload.detail);
    }
  } catch {
    // Fall through to a stable message.
  }
  return new Error(`request failed (${response.status})`);
}

async function authPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(apiUrl(path), withJsonBody({}, body));
  if (!response.ok) {
    throw await responseError(response);
  }
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export function fetchAuthHealth(): Promise<AuthHealth> {
  return fetch(apiUrl("/api/auth/health")).then(async (response) => {
    if (!response.ok) throw await responseError(response);
    return response.json() as Promise<AuthHealth>;
  });
}

export function loginAuth(email: string, password: string): Promise<AuthTokenPair> {
  return authPost<AuthTokenPair>("/api/auth/login", { email, password });
}

export function registerAuth(email: string, password: string): Promise<AuthTokenPair> {
  return authPost<AuthTokenPair>("/api/auth/register", { email, password });
}

export async function refreshAuthTokens(): Promise<AuthTokenPair | null> {
  if (refreshPromise) return refreshPromise;
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearAuthTokens();
    return null;
  }
  refreshPromise = authPost<AuthTokenPair>("/api/auth/refresh", { refresh_token: refreshToken })
    .then((tokens) => {
      setAuthTokens(tokens);
      return tokens;
    })
    .catch(() => {
      clearAuthTokens();
      return null;
    })
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

export async function logoutAuth(): Promise<void> {
  const refreshToken = getRefreshToken();
  try {
    if (refreshToken) {
      await authPost<void>("/api/auth/logout", { refresh_token: refreshToken });
    }
  } finally {
    clearAuthTokens();
  }
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

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(apiUrl(path), withAuth(init));
  if (response.status !== 401 || path.startsWith("/api/auth/")) {
    return response;
  }
  const tokens = await refreshAuthTokens();
  if (!tokens) return response;
  return fetch(apiUrl(path), withAuth(init));
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
