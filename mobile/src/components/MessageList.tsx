import { useRef } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";

import { colors, radius, spacing } from "../theme";
import type { Message } from "../types";
import { MessageBubble } from "./MessageBubble";

type Props = {
  messages: Message[];
  sending: boolean;
  language: string;
};

// The zero-message state is handled by the Welcome screen (see App). This list
// renders only once a conversation is active.
export function MessageList({ messages, sending, language }: Props) {
  const listRef = useRef<FlatList<Message>>(null);

  const scrollToEnd = () => listRef.current?.scrollToEnd({ animated: true });

  return (
    <FlatList
      ref={listRef}
      data={messages}
      keyExtractor={(m) => m.id}
      renderItem={({ item }) => <MessageBubble message={item} language={language} />}
      contentContainerStyle={styles.content}
      onContentSizeChange={scrollToEnd}
      onLayout={scrollToEnd}
      keyboardShouldPersistTaps="handled"
      ListFooterComponent={
        sending ? (
          <View style={styles.thinkingRow}>
            <Text style={styles.avatar}>🕉️</Text>
            <View style={styles.thinkingBubble}>
              <ActivityIndicator size="small" color={colors.gold} />
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
