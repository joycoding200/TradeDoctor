import { apiGet, apiPost } from "./client";

export async function runAnalysis(ds?: string, de?: string): Promise<any> {
  const params = new URLSearchParams();
  if (ds) params.set("date_start", ds);
  if (de) params.set("date_end", de);
  const qs = params.toString();
  return apiPost(`/api/analysis/run${qs ? `?${qs}` : ""}`);
}

export async function getStats(id: string): Promise<any> {
  return apiGet(`/api/analysis/${id}/stats`);
}

export async function getInsight(id: string): Promise<any> {
  return apiGet(`/api/analysis/${id}/insight`);
}

export async function getWhatIf(id: string): Promise<any> {
  return apiGet(`/api/analysis/${id}/whatif`);
}
