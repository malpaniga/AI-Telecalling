/**
 * Return the base WebSocket URL for the backend runtime.
 * In local dev (localhost / 127.0.0.1): ws://localhost:8000 (or wss: if https)
 * In production (Vercel or any deployed domain): wss://92.5.149.29.sslip.io
 * Can be overridden by NEXT_PUBLIC_WS_BASE or NEXT_PUBLIC_API_BASE.
 */
export function getBackendWsBase(): string {
  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_WS_BASE) {
    return process.env.NEXT_PUBLIC_WS_BASE.replace(/\/+$/, "");
  }

  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_BASE) {
    const base = process.env.NEXT_PUBLIC_API_BASE.replace(/\/+$/, "");
    if (base.startsWith("https://")) {
      return base.replace(/^https:\/\//, "wss://");
    }
    if (base.startsWith("http://")) {
      return base.replace(/^http:\/\//, "ws://");
    }
  }

  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    const isLocalhost = hostname === "localhost" || hostname === "127.0.0.1";

    if (isLocalhost) {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//localhost:8000`;
    }
  }

  // Production default via secure SSL sslip.io domain
  return "wss://92.5.149.29.sslip.io";
}
