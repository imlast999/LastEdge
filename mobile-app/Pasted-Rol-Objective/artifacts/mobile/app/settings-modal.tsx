/**
 * Settings Modal Screen
 * 
 * Accessible via modal/push navigation from main tabs
 * Not part of the tab navigator
 */
import React, { useCallback, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Platform,
  TouchableOpacity,
  Alert,
  TextInput,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { Feather } from "@expo/vector-icons";
import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import * as Haptics from "expo-haptics";

import { useColors } from "@/hooks/useColors";
import { useTrading } from "@/context/TradingContext";
import {
  useSettings,
  POLL_INTERVAL_OPTIONS,
  DEFAULT_SETTINGS,
} from "@/context/SettingsContext";
import { SettingsSection } from "@/components/settings/SettingsSection";
import { SettingsRow } from "@/components/settings/SettingsRow";
import { SettingsToggle } from "@/components/settings/SettingsToggle";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  getBuildApiUrl,
  getBuildApiSecret,
  resolveApiConfig,
  maskSecret,
  getAppVersion,
} from "@/lib/apiConfig";
import { testServerConnection } from "@/services/connectionTest";
import {
  registerForPushNotificationsAsync,
  sendLocalNotification,
} from "@/services/notifications";

export default function SettingsModalScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { t } = useTranslation();
  const { settings, updateSetting, resetSettings } = useSettings();
  const { refresh } = useTrading();

  const [urlDraft, setUrlDraft] = useState(settings.serverUrl);
  const [tokenDraft, setTokenDraft] = useState(settings.serverToken);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [permStatus, setPermStatus] = useState<string | null>(null);

  const topPad = insets.top;
  const bottomPad = Platform.OS === "web" ? 34 : insets.bottom;

  const handleTestConnection = useCallback(async () => {
    setTesting(true);
    setTestResult(null);
    if (settings.hapticsEnabled) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light).catch(() => {});
    }
    const result = await testServerConnection({
      apiUrl: urlDraft.trim(),
      apiSecret: tokenDraft.trim(),
    });
    if (result.success) {
      const s = result.data!;
      setTestResult(
        `OK · ${result.latencyMs} ms · MT5 ${s.connected ? "conectado" : "desconectado"} · ${s.equity.toFixed(2)} €`
      );
    } else {
      setTestResult(result.error ?? "No se pudo conectar al servidor");
    }
    setTesting(false);
  }, [settings.hapticsEnabled, urlDraft, tokenDraft]);

  const saveConnection = useCallback(() => {
    updateSetting("serverUrl", urlDraft.trim());
    updateSetting("serverToken", tokenDraft.trim());
    Alert.alert("Guardado", "Conexión actualizada. La app recargará datos automáticamente.");
  }, [urlDraft, tokenDraft, updateSetting]);

  const handleRequestPermissions = useCallback(async () => {
    const token = await registerForPushNotificationsAsync();
    const { status: perm } = await Notifications.getPermissionsAsync();
    setPermStatus(
      perm === "granted"
        ? token
          ? "Permisos concedidos · push activo"
          : "Permisos concedidos · notificaciones locales"
        : "Permisos denegados — actívalos en Ajustes del sistema"
    );
  }, []);

  const handleTestNotification = useCallback(async () => {
    await sendLocalNotification(
      "NEW_SIGNAL",
      "🔔 Notificación de prueba",
      "Si ves esto, las alertas locales funcionan correctamente."
    );
    if (settings.hapticsEnabled) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    }
  }, [settings.hapticsEnabled]);

  const handleClearBadge = useCallback(async () => {
    await Notifications.setBadgeCountAsync(0);
    Alert.alert("Listo", "Contador de notificaciones reiniciado.");
  }, []);

  const handleResetSettings = useCallback(() => {
    Alert.alert(
      "Restablecer ajustes",
      "¿Volver a la configuración predeterminada?",
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Restablecer",
          style: "destructive",
          onPress: async () => {
            await resetSettings();
            Alert.alert("Hecho", "Ajustes restablecidos.");
          },
        },
      ]
    );
  }, [resetSettings]);

  const handleClose = () => {
    router.back();
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={[
        styles.content,
        { paddingTop: topPad + 16, paddingBottom: bottomPad + 24 },
      ]}
      showsVerticalScrollIndicator={false}
    >
      <ApiErrorBanner />

      {/* Header with Close Button */}
      <View style={styles.header}>
        <View style={styles.headerContent}>
          <Text style={[styles.title, { color: colors.foreground }]}>Settings</Text>
          <Text style={[styles.subtitle, { color: colors.mutedForeground }]}>
            Connection, notifications, preferences
          </Text>
        </View>
        <TouchableOpacity
          onPress={handleClose}
          style={[styles.closeButton, { backgroundColor: colors.secondary }]}
        >
          <Feather name="x" size={24} color={colors.foreground} />
        </TouchableOpacity>
      </View>

      {/* Connection Settings */}
      <SettingsSection title="Server Connection" colors={colors}>
        <SettingsRow label="API URL" colors={colors}>
          <TextInput
            style={[styles.input, { color: colors.foreground, borderColor: colors.border }]}
            placeholder="https://api.example.com"
            placeholderTextColor={colors.mutedForeground}
            value={urlDraft}
            onChangeText={setUrlDraft}
            editable={true}
          />
        </SettingsRow>
        <SettingsRow label="API Secret" colors={colors}>
          <TextInput
            style={[styles.input, { color: colors.foreground, borderColor: colors.border }]}
            placeholder="••••••••"
            placeholderTextColor={colors.mutedForeground}
            value={tokenDraft}
            onChangeText={setTokenDraft}
            secureTextEntry
            editable={true}
          />
        </SettingsRow>
        <TouchableOpacity
          onPress={saveConnection}
          style={[styles.button, { backgroundColor: colors.primary }]}
        >
          <Text style={[styles.buttonText, { color: colors.primaryForeground }]}>
            Save Connection
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          onPress={handleTestConnection}
          disabled={testing}
          style={[styles.button, { backgroundColor: colors.secondary }]}
        >
          {testing ? (
            <ActivityIndicator color={colors.foreground} />
          ) : (
            <Text style={[styles.buttonText, { color: colors.foreground }]}>
              Test Connection
            </Text>
          )}
        </TouchableOpacity>
        {testResult && (
          <Text style={[styles.resultText, { color: colors.foreground }]}>
            {testResult}
          </Text>
        )}
      </SettingsSection>

      {/* Notifications */}
      <SettingsSection title="Notifications" colors={colors}>
        <TouchableOpacity
          onPress={handleRequestPermissions}
          style={[styles.button, { backgroundColor: colors.secondary }]}
        >
          <Text style={[styles.buttonText, { color: colors.foreground }]}>
            Request Permissions
          </Text>
        </TouchableOpacity>
        {permStatus && (
          <Text style={[styles.resultText, { color: colors.foreground }]}>
            {permStatus}
          </Text>
        )}
        <SettingsToggle
          label="Sound Enabled"
          value={settings.soundEnabled}
          onToggle={(v) => updateSetting("soundEnabled", v)}
          colors={colors}
        />
        <SettingsToggle
          label="Haptics Enabled"
          value={settings.hapticsEnabled}
          onToggle={(v) => updateSetting("hapticsEnabled", v)}
          colors={colors}
        />
        <TouchableOpacity
          onPress={handleTestNotification}
          style={[styles.button, { backgroundColor: colors.secondary }]}
        >
          <Text style={[styles.buttonText, { color: colors.foreground }]}>
            Test Notification
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          onPress={handleClearBadge}
          style={[styles.button, { backgroundColor: colors.secondary }]}
        >
          <Text style={[styles.buttonText, { color: colors.foreground }]}>
            Clear Badge
          </Text>
        </TouchableOpacity>
      </SettingsSection>

      {/* Reset */}
      <SettingsSection title="Advanced" colors={colors}>
        <TouchableOpacity
          onPress={handleResetSettings}
          style={[styles.button, { backgroundColor: colors.destructive }]}
        >
          <Text style={[styles.buttonText, { color: "white" }]}>
            Reset All Settings
          </Text>
        </TouchableOpacity>
      </SettingsSection>

      {/* Build Info */}
      <View style={styles.footer}>
        <Text style={[styles.footerText, { color: colors.mutedForeground }]}>
          LastEdge v{getAppVersion()}
        </Text>
        <Text style={[styles.footerText, { color: colors.mutedForeground }]}>
          Build {Constants.expoConfig?.version || "unknown"}
        </Text>
      </View>
    </ScrollView>
  );
}

// Import useTranslation here to avoid circular imports
import { useTranslation } from "@/hooks/useTranslation";

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingHorizontal: 16, gap: 24 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
  },
  headerContent: { flex: 1 },
  title: { fontSize: 28, fontFamily: "Inter_700Bold" },
  subtitle: { fontSize: 13, fontFamily: "Inter_400Regular", marginTop: 2 },
  closeButton: {
    width: 40,
    height: 40,
    borderRadius: 8,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 2,
  },
  input: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    fontFamily: "Inter_400Regular",
  },
  button: {
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 8,
  },
  buttonText: {
    fontSize: 14,
    fontFamily: "Inter_600SemiBold",
  },
  resultText: {
    fontSize: 12,
    fontFamily: "Inter_400Regular",
    marginTop: 8,
  },
  footer: {
    alignItems: "center",
    gap: 4,
    paddingTop: 16,
  },
  footerText: {
    fontSize: 11,
    fontFamily: "Inter_400Regular",
  },
});
