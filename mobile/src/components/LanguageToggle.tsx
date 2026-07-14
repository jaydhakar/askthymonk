import { Pressable, StyleSheet, Text, View } from "react-native";

import type { LanguageInfo } from "../api";
import { colors, radius, spacing } from "../theme";

type Props = {
  languages: LanguageInfo[];
  selected: string;
  onSelect: (code: string) => void;
};

/**
 * Segmented pill control populated entirely from the backend's /api/languages.
 * Renders one pill per language the backend reports (Hindi and English today);
 * adding more languages requires no client change.
 */
export function LanguageToggle({ languages, selected, onSelect }: Props) {
  if (languages.length === 0) return null;

  return (
    <View style={styles.container}>
      {languages.map((lang) => {
        const active = lang.code === selected;
        return (
          <Pressable
            key={lang.code}
            onPress={() => onSelect(lang.code)}
            accessibilityRole="button"
            accessibilityState={{ selected: active }}
            style={[styles.pill, active && styles.pillActive]}
          >
            <Text style={[styles.label, active && styles.labelActive]}>{lang.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    backgroundColor: colors.surfaceAlt,
    borderRadius: radius.pill,
    padding: 3,
    gap: 2,
  },
  pill: {
    paddingVertical: spacing.xs + 2,
    paddingHorizontal: spacing.md,
    borderRadius: radius.pill,
  },
  pillActive: {
    backgroundColor: colors.clay,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.textSecondary,
  },
  labelActive: {
    color: colors.onClay,
  },
});
