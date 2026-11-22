const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)tal_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/** Cookie session requests; adds X-CSRF-Token on mutating methods when the cookie is set. */
export function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const method = (init?.method ?? "GET").toUpperCase();
  const headers = new Headers(init?.headers);
  if (UNSAFE_METHODS.has(method)) {
    const csrf = getCsrfToken();
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }
  return fetch(input, { credentials: "include", ...init, headers });
}