import { useEffect, useState } from "react";
import { Alert, Animated, Dimensions, Pressable, StyleSheet, Text, View } from "react-native";

import { strings } from "../i18n";
import { colors, fonts, radius, spacing } from "../theme";

const DRAWER_W = Math.min(320, Math.round(Dimensions.get("window").width * 0.82));

type Props = {
  open: boolean;
  onClose: () => void;
  onNewConversation: () => void;
  language: string;
};

/**
 * Minimal slide-in side drawer. Always mounted as an absolute overlay and driven
 * purely by Animated (no Modal, no gesture/navigation native modules) so it runs
 * in the current dev client. When closed it slides off-screen and ignores touches.
 */
export function Drawer({ open, onClose, onNewConversation, language }: Props) {
  const s = strings(language);
  const [tx] = useState(() => new Animated.Value(-DRAWER_W));
  const [fade] = useState(() => new Animated.Value(0));

  useEffect(() => {
    Animated.parallel([
      Animated.timing(tx, {
        toValue: open ? 0 : -DRAWER_W,
        duration: open ? 220 : 200,
        useNativeDriver: true,
      }),
      Animated.timing(fade, {
        toValue: open ? 1 : 0,
        duration: open ? 220 : 200,
        useNativeDriver: true,
      }),
    ]).start();
  }, [open, tx, fade]);

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents={open ? "auto" : "none"}>
      <Animated.View style={[StyleSheet.absoluteFill, styles.backdrop, { opacity: fade }]}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="Close menu" />
      </Animated.View>

      <Animated.View style={[styles.panel, { transform: [{ translateX: tx }] }]}>
        <Text style={styles.brand}>{s.appName}</Text>
        <Text style={styles.tagline}>{s.drawerTagline}</Text>

        <View style={styles.rule} />

        <DrawerItem
          label={s.drawerNewConversation}
          onPress={() => {
            onNewConversation();
            onClose();
          }}
        />
        <DrawerItem label={s.drawerAbout} onPress={() => Alert.alert(s.appName, s.aboutBody)} />
      </Animated.View>
    </View>
  );
}

function DrawerItem({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={({ pressed }) => [styles.item, pressed && styles.itemPressed]}
    >
      <Text style={styles.itemText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    backgroundColor: colors.overlay,
  },
  panel: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    width: DRAWER_W,
    backgroundColor: colors.surface,
    borderRightWidth: StyleSheet.hairlineWidth,
    borderRightColor: colors.border,
    paddingTop: 56,
    paddingHorizontal: spacing.xl,
  },
  brand: {
    fontFamily: fonts.serif,
    fontSize: 24,
    color: colors.gold,
  },
  tagline: {
    fontSize: 13,
    color: colors.textMuted,
    marginTop: spacing.xs,
  },
  rule: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.border,
    marginVertical: spacing.lg,
  },
  item: {
    paddingVertical: spacing.md,
    borderRadius: radius.md,
    paddingHorizontal: spacing.sm,
  },
  itemPressed: {
    backgroundColor: "rgba(227,177,92,0.10)",
  },
  itemText: {
    fontSize: 16,
    color: colors.textPrimary,
  },
});
