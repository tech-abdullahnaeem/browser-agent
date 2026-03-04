/* ── REST API client for the browser-agent backend ── */

import type {
  TaskRequest,
  TaskCreateResponse,
  TaskResult,
  TaskListResponse,
} from "@/types/task";

const DEFAULT_BASE_URL = "http://localhost:8000";

let _baseUrl = DEFAULT_BASE_URL;

/** Update the base URL (e.g. from chrome.storage) */
export function setBaseUrl(url: string) {
  _baseUrl = url.replace(/\/+$/, "");
}

export function getBaseUrl(): string {
  return _baseUrl;
}

/** Load base URL from chrome.storage.local if available */
export async function loadBaseUrl(): Promise<string> {
  try {
    const result = await chrome.storage.local.get("backend_url");
    if (result.backend_url) {
      setBaseUrl(result.backend_url);
    }
  } catch {
    // Not in extension context (e.g. testing), use default
  }
  return _baseUrl;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${_baseUrl}${path}`;
  const resp = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!resp.ok) {
    const body = await resp.text().catch(() => "");
    throw new Error(`API ${resp.status}: ${body || resp.statusText}`);
  }

  return resp.json() as Promise<T>;
}

/* ── Task endpoints ── */

export async function submitTask(req: TaskRequest): Promise<TaskCreateResponse> {
  return request<TaskCreateResponse>("/api/tasks", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getTasks(
  limit = 20,
  offset = 0,
): Promise<TaskListResponse> {
  return request<TaskListResponse>(
    `/api/tasks?limit=${limit}&offset=${offset}`,
  );
}

export async function getTask(taskId: string): Promise<TaskResult> {
  return request<TaskResult>(`/api/tasks/${taskId}`);
}

export async function cancelTask(taskId: string): Promise<void> {
  await request<unknown>(`/api/tasks/${taskId}`, { method: "DELETE" });
}

/* ── Config endpoints ── */

export interface AgentConfig {
  max_steps: number;
  max_failures: number;
  use_vision: boolean;
  headless: boolean;
  wait_between_actions: number;
  max_actions_per_step: number;
  enable_planning: boolean;
  flash_model: string;
  pro_model: string;
}

export async function getConfig(): Promise<AgentConfig> {
  return request<AgentConfig>("/api/config");
}

export async function updateConfig(
  partial: Partial<AgentConfig>,
): Promise<AgentConfig> {
  return request<AgentConfig>("/api/config", {
    method: "PUT",
    body: JSON.stringify(partial),
  });
}

/* ── Health check ── */

export async function healthCheck(): Promise<boolean> {
  try {
    const data = await request<{ status: string }>("/health");
    return data.status === "ok";
  } catch {
    return false;
  }
}
