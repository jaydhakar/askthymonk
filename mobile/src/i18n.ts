/**
 * All user-facing UI strings, in one place.
 *
 * Scope note: crisis messages and the "I have not spoken…" decline are localized
 * by the BACKEND and arrive already-translated in the API response — they are
 * deliberately not duplicated here. Book titles are also intentionally NOT
 * translated/transliterated; they render exactly as stored.
 */

export type Strings = {
  appName: string;
  greetingTop: string;
  greetingBottom: string;
  suggestions: string[];
  inputPlaceholder: string;
  drawerTagline: string;
  drawerNewConversation: string;
  drawerAbout: string;
  aboutBody: string;
  loading: string;
  errorTitle: string;
  errorBody: string;
  voiceAlertTitle: string;
  micPermission: string;
  /** Display names for the language toggle, keyed by language code. */
  languageLabels: Record<string, string>;
  /** Citation source names (e.g. "Osho"), keyed by the backend's raw value. */
  sources: Record<string, string>;
};

// PROVISIONAL: Devanagari transliteration of "Ask Thy Monk", pending the user's
// choice among the options presented. Swap this one line once confirmed.
const HINDI_APP_NAME = "आस्क थाय मंक";

const en: Strings = {
  appName: "Ask Thy Monk",
  greetingTop: "Peace, seeker.",
  greetingBottom: "What weighs on your mind today?",
  suggestions: ["How do I quiet my mind?", "How do I let go of anger?"],
  inputPlaceholder: "Ask your question…",
  drawerTagline: "Wisdom, whenever you need it",
  drawerNewConversation: "New conversation",
  drawerAbout: "About",
  aboutBody:
    "Ask a question and receive a short reflection drawn from the indexed talks. Available in Hindi and English, by text or voice.",
  loading: "Loading…",
  errorTitle: "Couldn’t reach the backend",
  errorBody: "Could not reach the backend. Confirm it is running and that the address below is correct.",
  voiceAlertTitle: "Voice input",
  micPermission: "Microphone and speech-recognition permission are needed for voice input.",
  languageLabels: { hi: "Hindi", en: "English" },
  sources: { Osho: "Osho" },
};

const hi: Strings = {
  appName: HINDI_APP_NAME,
  greetingTop: "शांति, साधक।",
  greetingBottom: "आज आपके मन पर क्या बोझ है?",
  suggestions: ["मन को शांत कैसे करें?", "क्रोध को कैसे छोड़ें?"],
  inputPlaceholder: "अपना प्रश्न पूछें…",
  drawerTagline: "जब भी ज़रूरत हो, ज्ञान",
  drawerNewConversation: "नई बातचीत",
  drawerAbout: "परिचय",
  aboutBody:
    "प्रश्न पूछें और अनुक्रमित प्रवचनों से एक संक्षिप्त चिंतन प्राप्त करें। हिंदी और अंग्रेज़ी में, लिखकर या बोलकर उपलब्ध।",
  loading: "लोड हो रहा है…",
  errorTitle: "सर्वर से संपर्क नहीं हो सका",
  errorBody: "सर्वर से संपर्क नहीं हो सका। सुनिश्चित करें कि वह चल रहा है और नीचे दिया गया पता सही है।",
  voiceAlertTitle: "आवाज़ इनपुट",
  micPermission: "आवाज़ इनपुट के लिए माइक्रोफ़ोन और वाक्-पहचान की अनुमति आवश्यक है।",
  languageLabels: { hi: "हिंदी", en: "अंग्रेज़ी" },
  sources: { Osho: "ओशो" },
};

const ALL: Record<string, Strings> = { en, hi };

/** Strings for a language code, falling back to English for anything unknown. */
export function strings(language: string): Strings {
  return ALL[language] ?? en;
}

/**
 * Localized citation source name. Unknown sources (future Gita, Upanishads, …)
 * pass through unchanged rather than erroring or blanking.
 */
export function localizedSource(language: string, source: string): string {
  return strings(language).sources[source] ?? source;
}
