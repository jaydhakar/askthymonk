import { StyleSheet, Text, View } from "react-native";

import { formatBookTitle } from "../format";
import { colors, radius, spacing } from "../theme";
import type { Message } from "../types";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <View style={[styles.row, isUser ? styles.rowUser : styles.rowAssistant]}>
      <Text style={styles.avatar}>{isUser ? "🗣️" : "🕉️"}</Text>
      <View
        style={[
          styles.bubble,
          isUser ? styles.userBubble : styles.assistantBubble,
          message.error && styles.errorBubble,
        ]}
      >
        <Text style={[styles.text, message.error && styles.errorText]}>{message.text}</Text>
        {!isUser && !message.error && message.book ? (
          <Text style={styles.book}>— {formatBookTitle(message.book)}</Text>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "flex-end",
    marginVertical: spacing.xs + 2,
    gap: spacing.xs,
    maxWidth: "88%",
  },
  rowUser: {
    alignSelf: "flex-end",
    flexDirection: "row-reverse",
  },
  rowAssistant: {
    alignSelf: "flex-start",
  },
  avatar: {
    fontSize: 18,
    marginBottom: 2,
  },
  bubble: {
    paddingVertical: spacing.sm + 2,
    paddingHorizontal: spacing.md,
    borderRadius: radius.lg,
  },
  userBubble: {
    backgroundColor: colors.userBubble,
    borderBottomRightRadius: radius.sm,
  },
  assistantBubble: {
    backgroundColor: colors.assistantBubble,
    borderBottomLeftRadius: radius.sm,
  },
  errorBubble: {
    backgroundColor: "#F3DCD5",
  },
  text: {
    fontSize: 16,
    lineHeight: 23,
    color: colors.textPrimary,
  },
  errorText: {
    color: colors.danger,
  },
  book: {
    marginTop: spacing.xs + 2,
    fontSize: 12.5,
    fontStyle: "italic",
    color: colors.purpleDeep,
  },
});
