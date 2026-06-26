const BASE_URL = import.meta.env.VITE_API_BASE || "";

class AuthExpiredError extends Error {
  constructor() {
    super("Auth expired");
    this.name = "AuthExpiredError";
  }
}

function getToken(): string | null {
  return localStorage.getItem("token");
}

function onAuthExpired() {
  localStorage.removeItem("token");
  // Avoid redirect loop on login/register pages
  const path = window.location.pathname;
  if (path !== "/login" && path !== "/register" && path !== "/") {
    window.location.href = "/login?expired=1";
  }
}

function parseError(resp: Response): Promise<Error> {
  return resp.json().then(
    (body) => {
      let msg = "请求失败，请稍后重试";
      if (typeof body.detail === "string") {
        msg = body.detail;
      } else if (Array.isArray(body.detail) && body.detail.length > 0 && body.detail[0].msg) {
        msg = body.detail[0].msg; // Pydantic validation error fallback
      } else if (body.message) {
        msg = body.message;
      }
      return new Error(msg);
    },
    () => new Error("请求失败，请稍后重试")
  );
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
  const resp = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  // Login/register endpoints return 401 for bad credentials, not expired token.
  // Don't treat those as auth-expired — let the caller handle the error detail.
  const isAuthEndpoint = path.startsWith("/api/auth/login") || path.startsWith("/api/auth/register");
  if (resp.status === 401 && !isAuthEndpoint) {
    onAuthExpired();
    throw new AuthExpiredError();
  }
  return resp;
}

export async function apiPost(path: string, body?: unknown): Promise<any> {
  const resp = await apiFetch(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) throw await parseError(resp);
  return resp.json();
}

export async function apiGet(path: string): Promise<any> {
  const resp = await apiFetch(path);
  if (!resp.ok) throw await parseError(resp);
  return resp.json();
}

export async function apiUpload(path: string, formData: FormData): Promise<any> {
  const resp = await apiFetch(path, {
    method: "POST",
    body: formData,
  });
  if (!resp.ok) throw await parseError(resp);
  return resp.json();
}

export async function apiPut(path: string, body?: unknown): Promise<any> {
  const resp = await apiFetch(path, {
    method: "PUT",
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) throw await parseError(resp);
  return resp.json();
}

export async function apiDelete(path: string): Promise<any> {
  const resp = await apiFetch(path, { method: "DELETE" });
  if (!resp.ok) throw await parseError(resp);
  return resp.json();
}
