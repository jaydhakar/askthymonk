/**
 * Language preference: system-locale default on first launch ever, persisted
 * override thereafter.
 *
 * System-locale detection fires exactly ONCE, on the first launch when no
 * preference is stored. Every later launch reads the stored value instead.
 */

import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Localization from "expo-localization";

const STORAGE_KEY = "askthymonk.language";

/** Everything that isn't a clean Hindi match falls back to this. */
export const FALLBACK_LANGUAGE = "en";

/**
 * ONE rule: an exact Hindi locale match yields "hi". Anything else at all —
 * English, any other language, an undetermined/unrecognized locale, a throw, or
 * an unexpected shape — yields "en". No retries, no blocking.
 */
export function detectSystemLanguage(): string {
  try {
    const code = Localization.getLocales()?.[0]?.languageCode;
    return typeof code === "string" && code.toLowerCase() === "hi" ? "hi" : FALLBACK_LANGUAGE;
  } catch {
    return FALLBACK_LANGUAGE;
  }
}

export async function getStoredLanguage(): Promise<string | null> {
  try {
    return await AsyncStorage.getItem(STORAGE_KEY);
  } catch {
    return null; // treat an unreadable store as "no preference yet"
  }
}

/** Persist the user's choice so it survives restarts. Never throws. */
export async function storeLanguage(code: string): Promise<void> {
  try {
    await AsyncStorage.setItem(STORAGE_KEY, code);
  } catch {
    // Non-fatal: the app still works for this session.
  }
}

/**
 * The stored preference if one exists; otherwise detect from the system locale
 * once, persist that result, and use it.
 */
export async function resolveInitialLanguage(): Promise<string> {
  const stored = await getStoredLanguage();
  if (stored) return stored;

  const detected = detectSystemLanguage();
  await storeLanguage(detected);
  return detected;
}
