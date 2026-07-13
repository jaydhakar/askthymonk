import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { colors, radius, spacing } from "../theme";

type Props = {
  value: string;
  onChangeText: (text: string) => void;
  onSend: () => void;
  onMicPress: () => void;
  listening: boolean;
  sending: boolean;
  placeholder?: string;
};

export function ChatInput({
  value,
  onChangeText,
  onSend,
  onMicPress,
  listening,
  sending,
  placeholder,
}: Props) {
  const canSend = value.trim().length > 0 && !sending;

  return (
    <View style={styles.container}>
      <Pressable
        onPress={onMicPress}
        accessibilityRole="button"
        accessibilityLabel={listening ? "Stop listening" : "Start voice input"}
        style={[styles.micButton, listening && styles.micButtonActive]}
      >
        <Text style={styles.micIcon}>{listening ? "⏹" : "🎤"}</Text>
      </Pressable>

      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder ?? "Ask your question…"}
        placeholderTextColor={colors.textMuted}
        multiline
        editable={!sending}
        onSubmitEditing={canSend ? onSend : undefined}
        returnKeyType="send"
        blurOnSubmit={false}
      />

      <Pressable
        onPress={onSend}
        disabled={!canSend}
        accessibilityRole="button"
        accessibilityLabel="Send"
        style={[styles.sendButton, !canSend && styles.sendButtonDisabled]}
      >
        <Text style={styles.sendIcon}>➤</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: spacing.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surface,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  micButton: {
    width: 44,
    height: 44,
    borderRadius: radius.pill,
    backgroundColor: colors.surfaceAlt,
    alignItems: "center",
    justifyContent: "center",
  },
  micButtonActive: {
    backgroundColor: colors.clay,
  },
  micIcon: {
    fontSize: 18,
  },
  input: {
    flex: 1,
    minHeight: 44,
    maxHeight: 120,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm + 2,
    paddingBottom: spacing.sm + 2,
    backgroundColor: colors.background,
    borderRadius: radius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    fontSize: 16,
    color: colors.textPrimary,
  },
  sendButton: {
    width: 44,
    height: 44,
    borderRadius: radius.pill,
    backgroundColor: colors.clay,
    alignItems: "center",
    justifyContent: "center",
  },
  sendButtonDisabled: {
    backgroundColor: colors.border,
  },
  sendIcon: {
    fontSize: 18,
    color: colors.onClay,
    marginLeft: 2,
  },
});
