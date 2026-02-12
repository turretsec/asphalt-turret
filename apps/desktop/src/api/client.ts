// src/api/client.ts
export const API_BASE = "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  body?: string;
  constructor(status: number, message: string, body?: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function parseError(res: Response): Promise<string> {
  const ct = res.headers.get("content-type") || "";
  try {
    if (ct.includes("application/json")) {
      const j = await res.json();
      return j.detail ? JSON.stringify(j.detail) : JSON.stringify(j);
    }
    return await res.text();
  } catch {
    return "";
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const msg = (await parseError(res)) || `${path} failed: ${res.status}`;
    throw new ApiError(res.status, msg);
  }

  // Some endpoints may return 204 in the future
  if (res.status === 204) return undefined as T;

  return (await res.json()) as T;
}

export function apiGet<T>(path: string) {
  return request<T>("GET", path);
}

export function apiPatch<T>(path: string, body: unknown) {
  return request<T>("PATCH", path, body);
}

export function apiPost<T>(path: string, body: unknown) {
  return request<T>("POST", path, body);
}
