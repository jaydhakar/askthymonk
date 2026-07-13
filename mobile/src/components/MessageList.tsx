import { useRef } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";

import { colors, radius, spacing } from "../theme";
import type { Message } from "../types";
import { MessageBubble } from "./MessageBubble";

type Props = {
  messages: Message[];
  sending: boolean;
};

export function MessageList({ messages, sending }: Props) {
  const listRef = useRef<FlatList<Message>>(null);

  const scrollToEnd = () => listRef.current?.scrollToEnd({ animated: true });

  if (messages.length === 0 && !sending) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyMark}>🕉️</Text>
        <Text style={styles.emptyTitle}>Ask, and listen within</Text>
        <Text style={styles.emptyHint}>
          Pose a question about the mind, meditation, or life, and receive a short reflection.
        </Text>
      </View>
    );
  }

  return (
    <FlatList
      ref={listRef}
      data={messages}
      keyExtractor={(m) => m.id}
      renderItem={({ item }) => <MessageBubble message={item} />}
      contentContainerStyle={styles.content}
      onContentSizeChange={scrollToEnd}
      onLayout={scrollToEnd}
      keyboardShouldPersistTaps="handled"
      ListFooterComponent={
        sending ? (
          <View style={styles.thinkingRow}>
            <Text style={styles.avatar}>🕉️</Text>
            <View style={styles.thinkingBubble}>
              <ActivityIndicator size="small" color={colors.purple} />
            </View>
          </View>
        ) : null
      }
    />
  );
}

const styles = StyleSheet.create({
  content: {
    padding: spacing.lg,
    paddingBottom: spacing.xl,
  },
  empty: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xl,
    gap: spacing.sm,
  },
  emptyMark: {
    fontSize: 40,
    marginBottom: spacing.xs,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: colors.purpleDeep,
  },
  emptyHint: {
    fontSize: 14,
    color: colors.textMuted,
    textAlign: "center",
    lineHeight: 20,
  },
  thinkingRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    alignSelf: "flex-start",
    gap: spacing.xs,
    marginVertical: spacing.xs + 2,
  },
  avatar: {
    fontSize: 18,
    marginBottom: 2,
  },
  thinkingBubble: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.lg,
    borderBottomLeftRadius: radius.sm,
    backgroundColor: colors.assistantBubble,
  },
});
