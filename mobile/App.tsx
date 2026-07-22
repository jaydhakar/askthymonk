import { StatusBar } from "expo-status-bar";
import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  StatusBar as RNStatusBar,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { askWisdom, fetchLanguages, type LanguageInfo } from "./src/api";
import { ChatInput } from "./src/components/ChatInput";
import { Drawer } from "./src/components/Drawer";
import { Header } from "./src/components/Header";
import { MessageList } from "./src/components/MessageList";
import { Welcome } from "./src/components/Welcome";
import { API_BASE_URL } from "./src/config";
import { makeId, messagesToHistory } from "./src/format";
import { strings } from "./src/i18n";
import { resolveInitialLanguage, storeLanguage } from "./src/preferences";
import { colors, spacing } from "./src/theme";
import type { Message } from "./src/types";
import { sttLocale } from "./src/voice/locales";
import { speakAnswer, stopSpeaking } from "./src/voice/tts";
import { useSpeechToText } from "./src/voice/useSpeechToText";

/**
 * Dark, gold-accented chat app. Shows the Welcome/empty state (hero + greeting
 * + suggestions) until the first message, then the scrolling thread. Header,
 * input bar, and side drawer are persistent. Voice/language/backend logic is
 * unchanged — this file only orchestrates state and layout.
 */
export default function App() {
  const [languages, setLanguages] = useState<LanguageInfo[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    let mounted = true;
    (async () => {
      // Resolve the language preference alongside the languages fetch so the
      // locale/storage check never gates startup on its own. Timed so we can
      // report its real cost on-device.
      const t0 = Date.now();
      const preference = resolveInitialLanguage().then((code) => {
        console.log(`[startup] language preference resolved in ${Date.now() - t0}ms -> ${code}`);
        return code;
      });

      try {
        const [langs, pref] = await Promise.all([fetchLanguages(), preference]);
        if (!mounted) return;
        setLanguages(langs);
        // The stored/detected preference wins; fall back to the first language
        // the backend actually offers if it isn't available.
        const available = langs.map((l) => l.code);
        setSelected(available.includes(pref) ? pref : langs[0]?.code || pref);
      } catch (e) {
        if (!mounted) return;
        setLoadError(e instanceof Error ? e.message : "Failed to load languages.");
        // Still honor the preference so the error screen renders in-language.
        preference.then((pref) => mounted && setSelected((prev) => prev || pref));
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  // Persist the user's toggle choice so it survives restarts and is never
  // re-overridden by system-locale detection.
  const handleSelectLanguage = useCallback((code: string) => {
    setSelected(code);
    void storeLanguage(code);
  }, []);

  // Stop any speech when the app is torn down.
  useEffect(() => stopSpeaking, []);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || sending) return;

    // Prior turns of THIS conversation (before adding the new message), for
    // follow-up context. The API layer trims to the last 4.
    const history = messagesToHistory(messages);

    setMessages((prev) => [...prev, { id: makeId(), role: "user", text: question }]);
    setInput("");
    setSending(true);

    try {
      const res = await askWisdom(question, selected || "hi", history);
      setMessages((prev) => [
        ...prev,
        { id: makeId(), role: "assistant", text: res.answer, book: res.book, source: res.source },
      ]);
      // Auto-play the answer aloud in the selected language.
      speakAnswer(res.answer, selected || "hi");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Something went wrong. Please try again.";
      setMessages((prev) => [...prev, { id: makeId(), role: "assistant", text: msg, error: true }]);
    } finally {
      setSending(false);
    }
  }, [input, sending, selected, messages]);

  const handleNewConversation = useCallback(() => {
    stopSpeaking();
    setMessages([]);
    setInput("");
  }, []);

  const s = strings(selected);

  const { listening, toggle: toggleMic } = useSpeechToText({
    lang: sttLocale(selected),
    onTranscript: setInput,
    onError: (message) => Alert.alert(s.voiceAlertTitle, message),
    permissionMessage: s.micPermission,
  });

  return (
    <SafeAreaView style={styles.safe}>
      <Header
        languages={languages}
        selected={selected}
        onSelect={handleSelectLanguage}
        onMenuPress={() => setDrawerOpen(true)}
      />

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.gold} />
          <Text style={styles.muted}>{s.loading}</Text>
        </View>
      ) : loadError ? (
        <View style={styles.center}>
          <Text style={styles.errorTitle}>{s.errorTitle}</Text>
          <Text style={styles.muted}>{s.errorBody}</Text>
          <Text style={styles.url}>{API_BASE_URL}</Text>
        </View>
      ) : (
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          {messages.length === 0 ? (
            <Welcome onSelectSuggestion={setInput} language={selected} />
          ) : (
            <MessageList messages={messages} sending={sending} language={selected} />
          )}
          <ChatInput
            value={input}
            onChangeText={setInput}
            onSend={handleSend}
            onMicPress={toggleMic}
            listening={listening}
            sending={sending}
            placeholder={s.inputPlaceholder}
          />
        </KeyboardAvoidingView>
      )}

      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onNewConversation={handleNewConversation}
        language={selected}
      />

      <StatusBar style="light" />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background,
    paddingTop: Platform.OS === "android" ? RNStatusBar.currentHeight : 0,
  },
  flex: {
    flex: 1,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.xl,
    gap: spacing.sm,
  },
  muted: {
    fontSize: 14,
    color: colors.textMuted,
    textAlign: "center",
  },
  errorTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: colors.errorText,
    marginBottom: spacing.xs,
  },
  url: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
});
