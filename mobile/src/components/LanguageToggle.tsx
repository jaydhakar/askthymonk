import { Pressable, StyleSheet, Text, View } from "react-native";

import type { LanguageInfo } from "../api";
import { strings } from "../i18n";
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
            <Text style={[styles.label, active && styles.labelActive]}>
              {/* Localized name when we know it; otherwise the backend's label
                  (so future languages still render without a client change). */}
              {strings(selected).languageLabels[lang.code] ?? lang.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    backgroundColor: colors.pillBg,
    borderRadius: radius.pill,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    padding: 3,
    gap: 2,
  },
  pill: {
    paddingVertical: spacing.xs + 2,
    paddingHorizontal: spacing.md,
    borderRadius: radius.pill,
  },
  pillActive: {
    backgroundColor: colors.gold,
  },
  label: {
    fontSize: 13,
    fontWeight: "600",
    color: colors.textMuted,
  },
  labelActive: {
    color: colors.onGold,
  },
});
