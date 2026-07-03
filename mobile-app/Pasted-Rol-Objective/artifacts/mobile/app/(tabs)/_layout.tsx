import { BlurView } from "expo-blur";
import { Tabs, router } from "expo-router";
import { Feather } from "@expo/vector-icons";
import React from "react";
import {
  Platform,
  StyleSheet,
  TouchableOpacity,
  View,
  useColorScheme,
} from "react-native";

import { useColors } from "@/hooks/useColors";
import { useTranslation } from "@/hooks/useTranslation";

// ── Botón de ajustes que aparece en el header de todas las pantallas ──────────
function SettingsButton() {
  const colors = useColors();
  const { t } = useTranslation();
  return (
    <TouchableOpacity
      onPress={() => router.push("/(tabs)/settings" as any)}
      hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      style={styles.settingsBtn}
      accessibilityLabel={t("settingsTitle")}
      accessibilityRole="button"
    >
      <Feather name="settings" size={22} color={colors.foreground} />
    </TouchableOpacity>
  );
}

// ── Layout estándar Android / Web ─────────────────────────────────────────────
function ClassicTabLayout() {
  const colors = useColors();
  const { t } = useTranslation();
  const colorScheme = useColorScheme();
  const isIOS = Platform.OS === "ios";
  const isWeb = Platform.OS === "web";

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.mutedForeground,
        headerShown: true,
        headerStyle: { backgroundColor: colors.background },
        headerTintColor: colors.foreground,
        headerShadowVisible: false,
        headerRight: () => <SettingsButton />,
        tabBarStyle: {
          position: "absolute",
          backgroundColor: isIOS ? "transparent" : colors.background,
          borderTopWidth: 1,
          borderTopColor: colors.border,
          elevation: 0,
          ...(isWeb ? { height: 84 } : {}),
        },
        tabBarBackground: () =>
          isIOS ? (
            <BlurView intensity={80} tint="dark" style={StyleSheet.absoluteFill} />
          ) : isWeb ? (
            <View style={[StyleSheet.absoluteFill, { backgroundColor: colors.background }]} />
          ) : null,
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Dashboard",
          tabBarIcon: ({ color }) => <Feather name="bar-chart-2" size={22} color={color} />,
        }}
      />
      <Tabs.Screen
        name="trades"
        options={{
          title: "Trades",
          tabBarIcon: ({ color }) => <Feather name="repeat" size={22} color={color} />,
        }}
      />
      <Tabs.Screen
        name="backtests"
        options={{
          title: "Backtests",
          tabBarIcon: ({ color }) => <Feather name="activity" size={22} color={color} />,
        }}
      />
      <Tabs.Screen
        name="research"
        options={{
          title: "Research",
          tabBarIcon: ({ color }) => <Feather name="layers" size={22} color={color} />,
        }}
      />
      {/* Settings: oculta de la tab bar, título traducido */}
      <Tabs.Screen
        name="settings"
        options={{
          title: t("settingsTitle"),
          href: null,
        }}
      />
    </Tabs>
  );
}

export default function TabLayout() {
  return <ClassicTabLayout />;
}

const styles = StyleSheet.create({
  settingsBtn: {
    marginRight: 16,
    padding: 2,
  },
});
