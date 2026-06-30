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

// ── Botón de ajustes que aparece en el header de todas las pantallas ──────────
function SettingsButton() {
  const colors = useColors();
  return (
    <TouchableOpacity
      onPress={() => router.push("/settings")}
      hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      style={styles.settingsBtn}
      accessibilityLabel="Abrir ajustes"
      accessibilityRole="button"
    >
      <Feather name="settings" size={22} color={colors.foreground} />
    </TouchableOpacity>
  );
}

// ── Opciones de header compartidas ───────────────────────────────────────────
function sharedHeaderOptions(colors: ReturnType<typeof useColors>) {
  return {
    headerShown: true,
    headerStyle: {
      backgroundColor: colors.background,
    },
    headerTintColor: colors.foreground,
    headerShadowVisible: false,
    headerRight: () => <SettingsButton />,
  };
}

// ── Layout estándar Android / Web ─────────────────────────────────────────────
function ClassicTabLayout() {
  const colors = useColors();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";
  const isIOS = Platform.OS === "ios";
  const isWeb = Platform.OS === "web";

  const headerOpts = sharedHeaderOptions(colors);

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.mutedForeground,
        headerShown: true,
        headerStyle: headerOpts.headerStyle,
        headerTintColor: headerOpts.headerTintColor,
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
            <BlurView
              intensity={80}
              tint="dark"
              style={StyleSheet.absoluteFill}
            />
          ) : isWeb ? (
            <View
              style={[StyleSheet.absoluteFill, { backgroundColor: colors.background }]}
            />
          ) : null,
      }}
    >
      {/* ── Tab 1: Dashboard ── */}
      <Tabs.Screen
        name="index"
        options={{
          title: "Dashboard",
          tabBarIcon: ({ color }) => <Feather name="bar-chart-2" size={22} color={color} />,
        }}
      />

      {/* ── Tab 2: Trades (Pendientes + Cerradas) ── */}
      <Tabs.Screen
        name="trades"
        options={{
          title: "Trades",
          tabBarIcon: ({ color }) => <Feather name="repeat" size={22} color={color} />,
        }}
      />

      {/* ── Tab 3: Backtests ── */}
      <Tabs.Screen
        name="backtests"
        options={{
          title: "Backtests",
          tabBarIcon: ({ color }) => <Feather name="activity" size={22} color={color} />,
        }}
      />

      {/* ── Pantalla de Ajustes: oculta de la tab bar, accesible por push ── */}
      <Tabs.Screen
        name="settings"
        options={{
          title: "Ajustes",
          href: null, // oculto de la barra de navegación
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
