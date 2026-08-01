const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const TOKEN_KEY = "reportlens_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// Set by AuthProvider so a 401 anywhere in the app can trigger a logout+redirect without
// this module needing to import react-router or the auth context (would create a cycle).
let onUnauthorized: (() => void) | null = null;
export function registerUnauthorizedHandler(fn: () => void): void {
  onUnauthorized = fn;
}

async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) {
      // FastAPI validation errors: [{loc, msg, type}, ...]
      return body.detail.map((d: { msg?: string }) => d.msg).join("; ");
    }
  } catch {
    // response wasn't JSON - fall through to the generic message
  }
  return `Request failed with status ${res.status}`;
}

interface RequestOptions {
  method?: string;
  body?: BodyInit;
  json?: unknown;
  auth?: boolean;
}

async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  let body = opts.body;

  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  }

  if (opts.auth !== false) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body,
  });

  // A 401 means two completely different things depending on the call. On an authenticated
  // request the token is bad or expired, so log the user out. On the login endpoint it just
  // means the password was wrong - hijacking that into "your session has expired" told users
  // their session died when they never had one, which is exactly what a mistyped password
  // does NOT need to say. There, let the server's own message through.
  if (res.status === 401 && opts.auth !== false) {
    clearToken();
    onUnauthorized?.();
    throw new ApiError(401, "Your session has expired. Please log in again.");
  }

  if (!res.ok) {
    throw new ApiError(res.status, await extractErrorMessage(res));
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  register: (email: string, password: string) =>
    request<{ id: number; email: string }>("/api/auth/register", {
      method: "POST",
      json: { email, password },
      auth: false,
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/api/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username: email, password }),
      auth: false,
    }),

  listReports: () => request<import("./types").ReportListItem[]>("/api/reports"),

  getReport: (id: number) => request<import("./types").Report>(`/api/reports/${id}`),

  uploadReport: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<import("./types").Report>("/api/reports", {
      method: "POST",
      body: formData,
    });
  },
};
