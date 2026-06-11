import { apiPost, apiUpload } from "./client";

export async function uploadFile(file: File): Promise<any> {
  const formData = new FormData();
  formData.append("file", file);
  return apiUpload("/api/upload", formData);
}

export async function confirmFormat(rawFileId: string, sourceType: string): Promise<any> {
  return apiPost("/api/upload/confirm", { raw_file_id: rawFileId, source_type: sourceType });
}

export async function importTrades(rawFileId: string): Promise<any> {
  return apiPost("/api/upload/import", { raw_file_id: rawFileId });
}
