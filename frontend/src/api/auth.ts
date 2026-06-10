import { apiPost } from "./client";

export async function login(email: string, password: string): Promise<string> {
  const data = await apiPost("/api/auth/login", { email, password });
  return data.access_token;
}

export async function register(email: string, password: string): Promise<string> {
  const data = await apiPost("/api/auth/register", { email, password });
  return data.access_token;
}
