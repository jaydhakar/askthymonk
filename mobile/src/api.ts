/**
 * Typed client for the Zen Wisdom Explorer backend.
 *
 * The base URL comes from src/config (EXPO_PUBLIC_API_URL) and is never
 * hardcoded here.
 */

import { API_BASE_URL, API_KEY } from "./config";

export type LanguageInfo = {
  code: string;
  label: string;
};

export type WisdomResponse = {
  answer: string;
  book: string | null;
  language: string;
};

/** Error carrying an HTTP status when the failure came from the server. */
export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

const DEFAULT_TIMEOUT_MS = 20000;

async function request<T>(path: string, init?: RequestInit, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
        ...(init?.headers ?? {}),
      },
    });

    if (!res.ok) {
      // Try to surface the backend's error detail if present.
      let detail = `Request failed (${res.status})`;
      try {
        const body = await res.json();
        if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      } catch {
        // non-JSON error body; keep the generic message
      }
      throw new ApiError(detail, res.status);
    }

    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof Error && err.name === "AbortError") {
      throw new ApiError("The request timed out. Check that the backend is reachable.");
    }
    throw new ApiError(
      "Could not reach the backend. Confirm it is running and that EXPO_PUBLIC_API_URL is correct."
    );
  } finally {
    clearTimeout(timer);
  }
}

/** GET /api/languages — the single source of truth for the language toggle. */
export async function fetchLanguages(): Promise<LanguageInfo[]> {
  const data = await request<{ languages: LanguageInfo[] }>("/api/languages");
  return data.languages ?? [];
}

/** POST /api/wisdom — ask a question in the selected language. */
export async function askWisdom(question: string, language: string): Promise<WisdomResponse> {
  return request<WisdomResponse>("/api/wisdom", {
    method: "POST",
    body: JSON.stringify({ question, language }),
  });
}
