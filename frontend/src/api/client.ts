const BASE_URL = "http://localhost:8000";

function getToken(): string | null {
  return localStorage.getItem("token");
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const isFormData = options.body instanceof FormData;
  if (!isFormData && options.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }
  return fetch(`${BASE_URL}${path}`, { ...options, headers });
}

export async function apiPost(path: string, body?: unknown): Promise<any> {
  const resp = await apiFetch(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return resp.json();
}

export async function apiGet(path: string): Promise<any> {
  const resp = await apiFetch(path);
  if (!resp.ok) throw new Error("Request failed");
  return resp.json();
}

export async function apiUpload(path: string, formData: FormData): Promise<any> {
  const token = getToken();
  const resp = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
  if (!resp.ok) throw new Error("Upload failed");
  return resp.json();
}
