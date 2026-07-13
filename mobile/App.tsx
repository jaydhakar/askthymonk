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
import { Header } from "./src/components/Header";
import { MessageList } from "./src/components/MessageList";
import { API_BASE_URL } from "./src/config";
import { makeId } from "./src/format";
import { colors, spacing } from "./src/theme";
import type { Message } from "./src/types";

/**
 * Milestone 3: full chat UI — message list, user/assistant bubbles with cited
 * book, input row (mic placeholder until m4) + send, and an in-flight
 * indicator. Sends questions to the backend via askWisdom.
 */
export default function App() {
  const [languages, setLanguages] = useState<LanguageInfo[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const langs = await fetchLanguages();
        if (!mounted) return;
        setLanguages(langs);
        setSelected((prev) => prev || langs[0]?.code || "hi");
      } catch (e) {
        if (!mounted) return;
        setLoadError(e instanceof Error ? e.message : "Failed to load languages.");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || sending) return;

    setMessages((prev) => [...prev, { id: makeId(), role: "user", text: question }]);
    setInput("");
    setSending(true);

    try {
      const res = await askWisdom(question, selected || "hi");
      setMessages((prev) => [
        ...prev,
        { id: makeId(), role: "assistant", text: res.answer, book: res.book },
      ]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Something went wrong. Please try again.";
      setMessages((prev) => [...prev, { id: makeId(), role: "assistant", text: msg, error: true }]);
    } finally {
      setSending(false);
    }
  }, [input, sending, selected]);

  const handleMicPress = useCallback(() => {
    // Placeholder until milestone 4 wires expo-speech-recognition.
    Alert.alert("Voice input", "Voice input arrives in the next milestone.");
  }, []);

  return (
    <SafeAreaView style={styles.safe}>
      <Header languages={languages} selected={selected} onSelect={setSelected} />

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.clay} />
          <Text style={styles.muted}>Loading…</Text>
        </View>
      ) : loadError ? (
        <View style={styles.center}>
          <Text style={styles.errorTitle}>Couldn’t reach the backend</Text>
          <Text style={styles.muted}>{loadError}</Text>
          <Text style={styles.url}>{API_BASE_URL}</Text>
        </View>
      ) : (
        <KeyboardAvoidingView
          style={styles.flex}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <MessageList messages={messages} sending={sending} />
          <ChatInput
            value={input}
            onChangeText={setInput}
            onSend={handleSend}
            onMicPress={handleMicPress}
            listening={false}
            sending={sending}
          />
        </KeyboardAvoidingView>
      )}

      <StatusBar style="dark" />
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
    color: colors.danger,
    marginBottom: spacing.xs,
  },
  url: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
});
