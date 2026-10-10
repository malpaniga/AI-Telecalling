export interface AuthUser {
  user_id: string;
  email: string;
  role: string;
  org_id: string | null;
  exp: number;
}

const TOKEN_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function isLoggedIn(): boolean {
  const token = getAccessToken();
  if (!token) return false;
  try {
    const user = decodeToken(token);
    return user.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

export function decodeToken(token: string): AuthUser {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("Invalid JWT format");
  const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
  return {
    user_id: payload.sub ?? payload.user_id ?? "",
    email: payload.email ?? "",
    role: payload.role ?? "",
    org_id: payload.org_id ?? null,
    exp: payload.exp ?? 0,
  };
}
