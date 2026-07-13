/**
 * App configuration derived from environment.
 *
 * The backend base URL is never hardcoded — it comes from EXPO_PUBLIC_API_URL
 * (see .env.example). Falls back to localhost for the simplest local case.
 */

const DEFAULT_API_URL = "http://localhost:8000";

export const API_BASE_URL = (
  process.env.EXPO_PUBLIC_API_URL ?? DEFAULT_API_URL
).replace(/\/+$/, "");

/**
 * Optional shared secret sent as X-API-Key. Must match the backend's
 * API_SHARED_SECRET. Empty (default) sends no key — fine for local dev.
 * Note: values baked into a public app bundle are extractable, so this only
 * deters casual direct hits on the backend URL.
 */
export const API_KEY = process.env.EXPO_PUBLIC_API_KEY ?? "";
