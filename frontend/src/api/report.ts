import { apiFetch, apiGet, apiPost } from "./client";

export async function generateReport(analysisId: string): Promise<any> {
  return apiPost("/api/report/generate", { analysis_id: analysisId });
}

export async function getReport(id: string): Promise<any> {
  return apiGet(`/api/report/${id}`);
}

export async function listReports(): Promise<any> {
  return apiGet("/api/reports");
}

export async function checkAnalysisReport(analysisId: string): Promise<{ exists: boolean; report_id: string }> {
  return apiGet(`/api/report/by-analysis/${analysisId}`);
}

export async function downloadReport(reportId: string): Promise<Blob> {
  const resp = await apiFetch(`/api/report/${reportId}/download`);
  if (!resp.ok) throw new Error("下载失败");
  return resp.blob();
}
