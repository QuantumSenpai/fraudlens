export class ApiError extends Error {
  constructor(message: string, public status: number, public requestId?: string, public retryAfter?: number) {
    super(message);
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/gateway/${path}`, { cache: "no-store", ...options });
  } catch {
    throw new ApiError("Cannot reach FraudLens. Check your connection and try again.", 0);
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message = response.status === 401 ? "Your session has expired. Sign in again to continue." : data?.error?.message || "The request could not be completed.";
    throw new ApiError(message, response.status, data?.request_id || response.headers.get("x-request-id") || undefined, Number(response.headers.get("retry-after")) || undefined);
  }
  if (data === null) throw new ApiError("FraudLens returned an empty or invalid response. Try again.", response.status, response.headers.get("x-request-id") || undefined);
  return data as T;
}

export function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    const suffix = error.retryAfter ? ` Try again in ${error.retryAfter} seconds.` : "";
    return `${error.message}${suffix}${error.requestId ? ` Request ID: ${error.requestId}.` : ""}`;
  }
  return error instanceof Error ? error.message : "Something went wrong. Try again.";
}
