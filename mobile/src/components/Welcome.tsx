import { Dimensions, Image, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { strings } from "../i18n";
import { colors, fonts, radius, spacing } from "../theme";

const HERO = require("../../assets/hero-monk.jpg");

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get("window");
const HERO_H = Math.round(SCREEN_H * 0.46);
// Full image is 768x1376; scale to screen width and pin to the top so the
// halo + face show (rather than the center-crop RN "cover" would give).
const IMG_H = Math.round(SCREEN_W * (1376 / 768));

type Props = {
  onSelectSuggestion: (text: string) => void;
  language: string;
};

/** Decorative divider: thin gold line — diamond — thin gold line. */
function Divider() {
  return (
    <View style={styles.divider}>
      <View style={styles.dividerLine} />
      <View style={styles.diamond} />
      <View style={styles.dividerLine} />
    </View>
  );
}

export function Welcome({ onSelectSuggestion, language }: Props) {
  const s = strings(language);
  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      <View style={styles.heroClip}>
        <Image source={HERO} style={styles.heroImage} resizeMode="cover" />
        {/* Soft fade so the hero blends into the near-black background. */}
        <View style={styles.heroFade} pointerEvents="none">
          {FADE_STEPS.map((opacity, i) => (
            <View key={i} style={[styles.fadeBand, { opacity }]} />
          ))}
        </View>
      </View>

      <View style={styles.body}>
        <Text style={styles.name}>{s.appName}</Text>
        <Divider />

        <Text style={styles.greetingTop}>{s.greetingTop}</Text>
        <Text style={styles.greetingBottom}>{s.greetingBottom}</Text>

        <View style={styles.pills}>
          {s.suggestions.map((text) => (
            <Pressable
              key={text}
              onPress={() => onSelectSuggestion(text)}
              accessibilityRole="button"
              accessibilityLabel={`Use suggestion: ${text}`}
              style={({ pressed }) => [styles.pill, pressed && styles.pillPressed]}
            >
              <Text style={styles.pillText}>{text}</Text>
            </Pressable>
          ))}
        </View>
      </View>
    </ScrollView>
  );
}

// Increasing-opacity bands approximate a gradient fade (no native gradient dep).
const FADE_STEPS = [0.0, 0.12, 0.28, 0.5, 0.75, 1.0];

const styles = StyleSheet.create({
  scroll: {
    flex: 1,
    backgroundColor: colors.background,
  },
  content: {
    paddingBottom: spacing.xl,
  },
  heroClip: {
    width: SCREEN_W,
    height: HERO_H,
    overflow: "hidden",
    backgroundColor: colors.background,
  },
  heroImage: {
    position: "absolute",
    top: 0,
    width: SCREEN_W,
    height: IMG_H,
  },
  heroFade: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    height: 96,
    flexDirection: "column",
  },
  fadeBand: {
    flex: 1,
    backgroundColor: colors.background,
  },
  body: {
    alignItems: "center",
    paddingHorizontal: spacing.xl,
    marginTop: -spacing.sm,
  },
  name: {
    fontFamily: fonts.serif,
    fontSize: 30,
    color: colors.gold,
    letterSpacing: 0.5,
  },
  divider: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: spacing.md,
    gap: spacing.sm,
  },
  dividerLine: {
    width: 44,
    height: 1,
    backgroundColor: colors.goldDim,
    opacity: 0.7,
  },
  diamond: {
    width: 8,
    height: 8,
    backgroundColor: colors.gold,
    transform: [{ rotate: "45deg" }],
  },
  greetingTop: {
    fontFamily: fonts.serif,
    fontSize: 19,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  greetingBottom: {
    fontFamily: fonts.serif,
    fontSize: 20,
    color: colors.gold,
    marginTop: spacing.xs,
    textAlign: "center",
  },
  pills: {
    marginTop: spacing.xl,
    width: "100%",
    gap: spacing.md,
  },
  pill: {
    backgroundColor: colors.pillBg,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.border,
    borderRadius: radius.pill,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    alignItems: "center",
  },
  pillPressed: {
    backgroundColor: "rgba(227,177,92,0.12)",
  },
  pillText: {
    color: colors.textPrimary,
    fontSize: 15,
  },
});
