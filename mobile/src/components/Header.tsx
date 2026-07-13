import { StyleSheet, Text, View } from "react-native";

import type { LanguageInfo } from "../api";
import { colors, spacing } from "../theme";
import { LanguageToggle } from "./LanguageToggle";

type Props = {
  languages: LanguageInfo[];
  selected: string;
  onSelect: (code: string) => void;
};

/** App header: title + the backend-driven language toggle. */
export function Header({ languages, selected, onSelect }: Props) {
  return (
    <View style={styles.container}>
      <View style={styles.titleRow}>
        <Text style={styles.mark}>🕉️</Text>
        <Text style={styles.title}>Zen Wisdom</Text>
      </View>
      <LanguageToggle languages={languages} selected={selected} onSelect={onSelect} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    backgroundColor: colors.surface,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    flexShrink: 1,
  },
  mark: {
    fontSize: 20,
  },
  title: {
    fontSize: 17,
    fontWeight: "700",
    color: colors.purpleDeep,
    flexShrink: 1,
  },
});
