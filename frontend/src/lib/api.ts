const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/** Default ceiling for mutating API calls. */
export const API_REQUEST_TIMEOUT_MS = 25_000;

/** Shorter window for workspace bootstrap so the auth gate fails fast on cold starts. */
export const BOOTSTRAP_REQUEST_TIMEOUT_MS = 15_000;

export function isTransientHttpStatus(status: number): boolean {
  return status === 429 || status === 502 || status === 503 || status === 504;
}

export function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
}

function linkedAbortSignal(parent: AbortSignal, timeoutMs: number): { signal: AbortSignal; dispose: () => void } {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const onParentAbort = () => {
    clearTimeout(timer);
    controller.abort();
  };
  if (parent.aborted) onParentAbort();
  else parent.addEventListener("abort", onParentAbort, { once: true });
  return {
    signal: controller.signal,
    dispose: () => {
      clearTimeout(timer);
      parent.removeEventListener("abort", onParentAbort);
    },
  };
}

export async function apiFetchWithTimeout(
  input: RequestInfo | URL,
  init?: RequestInit & { timeoutMs?: number },
): Promise<Response> {
  const timeoutMs = init?.timeoutMs ?? API_REQUEST_TIMEOUT_MS;
  const parent = init?.signal;
  if (!parent) {
    return apiFetch(input, { ...init, signal: AbortSignal.timeout(timeoutMs) });
  }
  const { signal, dispose } = linkedAbortSignal(parent, timeoutMs);
  try {
    return await apiFetch(input, { ...init, signal });
  } finally {
    dispose();
  }
}

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