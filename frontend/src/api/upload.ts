import { apiPost, apiUpload } from "./client";

export async function uploadFile(file: File): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  return apiUpload("/api/upload", formData);
}

export async function confirmFormat(rawFileId: string, sourceType: string): Promise<any> {
  return apiPost(`/api/upload/${rawFileId}/confirm`, { source_type: sourceType });
}

export async function importTrades(rawFileId: string): Promise<any> {
  return apiPost(`/api/upload/${rawFileId}/import`);
}
