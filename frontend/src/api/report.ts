import { apiGet, apiPost } from "./client";

export async function generateReport(analysisId: string): Promise<any> {
  return apiPost(`/api/report/${analysisId}/generate`);
}

export async function getReport(id: string): Promise<any> {
  return apiGet(`/api/report/${id}`);
}

export async function listReports(): Promise<any> {
  return apiGet("/api/report");
}
