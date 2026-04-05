import type { DashboardResponse } from '../types/dashboard';

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
