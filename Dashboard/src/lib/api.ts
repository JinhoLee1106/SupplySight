import type { DashboardResponse } from '../types/dashboard';

export type AgentChatMessage = {
  role: 'user' | 'assistant' | 'system';
  content: string;
};

export type AgentChatPayload = {
  messages: AgentChatMessage[];
  preferenceContext?: Record<string, unknown>;
  temperature?: number;
};

export type AgentChatResponse = {
  message: string;
  model?: string;
  createdAt?: string;
};

/**
 * In dev, Vite proxies `/api` to the FastAPI server (see `vite.config.ts`).
 * For production or split deploys, set `VITE_API_BASE_URL` to the API origin (no trailing slash).
 */
export async function fetchDashboard(): Promise<DashboardResponse> {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';
  const url = `${base}/api/dashboard`;
  const res = await fetch(url);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed (${res.status})`);
  }
  return res.json() as Promise<DashboardResponse>;
}

export async function postAgentChat(payload: AgentChatPayload): Promise<AgentChatResponse> {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '';
  const url = `${base}/api/agents/chat`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      const text = await res.text();
      detail = text || detail;
    }
    throw new Error(detail);
  }

  return res.json() as Promise<AgentChatResponse>;
}
