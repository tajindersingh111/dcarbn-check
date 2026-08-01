export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const baseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${encodeURIComponent(name)}=`;
  const value = document.cookie
    .split("; ")
    .find((item) => item.startsWith(prefix));
  return value ? decodeURIComponent(value.slice(prefix.length)) : null;
}

async function parseResponse(response: Response): Promise<unknown> {
  if (response.status === 204) return null;
  return response.json().catch(() => ({ detail: response.statusText }));
}

async function refreshSession(): Promise<boolean> {
  const response = await fetch(`${baseUrl}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" }
  });
  return response.ok;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  allowRefresh = true
): Promise<T> {
  const headers = new Headers(options.headers);
  const csrfToken = getCookie("dcarbn_csrf");

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (
    csrfToken &&
    !["GET", "HEAD", "OPTIONS"].includes((options.method ?? "GET").toUpperCase())
  ) {
    headers.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers,
    credentials: "include",
    cache: "no-store"
  });

  if (response.status === 401 && allowRefresh && !path.startsWith("/auth/")) {
    if (await refreshSession()) {
      return apiRequest<T>(path, options, false);
    }
  }

  const body = await parseResponse(response);
  if (!response.ok) {
    const detail =
      typeof (body as { detail?: unknown })?.detail === "string"
        ? String((body as { detail: string }).detail)
        : "The request could not be completed.";
    throw new ApiError(detail, response.status, body);
  }
  return body as T;
}
