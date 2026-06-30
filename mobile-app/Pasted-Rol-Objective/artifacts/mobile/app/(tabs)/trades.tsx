/**
 * Pantalla Trades — dos sub-tabs internos:
 *   • Pendientes: señales con status "pending" (requieren acción) +
 *                 señales con status "active" (posición abierta)
 *   • Cerradas:   trades cerrados (WIN / LOSS / BREAKEVEN)
 */
import React, { useMemo, useState } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  Platform,
  TouchableOpacity,
  RefreshControl,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";

import { useColors } from "@/hooks/useColors";
import { useTrading } from "@/context/TradingContext";
import { SignalCard } from "@/components/SignalCard";
import { TradeCard } from "@/components/TradeCard";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";

type SubTab = "pending" | "closed";

export default function TradesScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const {
    signals,
    trades,
    acceptSignal,
    rejectSignal,
    loading,
    refresh,
  } = useTrading();

  const [activeTab, setActiveTab] = useState<SubTab>("pending");

  const bottomPad = Platform.OS === "web" ? 34 : 0;

  // Pendientes = señales que necesitan acción o ya están abiertas en MT5
  const pendingSignals = useMemo(
    () =>
      [...signals]
        .filter((s) => s.status === "pending" || s.status === "active")
        .sort((a, b) => {
          // Primero "pending" (requieren acción), luego "active"
          if (a.status === "pending" && b.status !== "pending") return -1;
          if (a.status !== "pending" && b.status === "pending") return 1;
          return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
        }),
    [signals]
  );

  // Cerradas: trades con resultado definitivo
  const closedTrades = useMemo(
    () =>
      [...trades].sort(
        (a, b) => new Date(b.closedAt).getTime() - new Date(a.closedAt).getTime()
      ),
    [trades]
  );

  // Estadísticas para la sub-tab "Cerradas"
  const wins = closedTrades.filter((t) => t.profit > 0).length;
  const losses = closedTrades.filter((t) => t.profit <= 0).length;
  const totalProfit = closedTrades
    .filter((t) => t.profit > 0)
    .reduce((s, t) => s + t.profit, 0);
  const totalLoss = Math.abs(
    closedTrades.filter((t) => t.profit < 0).reduce((s, t) => s + t.profit, 0)
  );
  const profitFactor =
    totalLoss > 0 ? (totalProfit / totalLoss).toFixed(2) : "∞";
  const totalPnL = closedTrades.reduce((s, t) => s + t.profit, 0);

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {/* ── Sub-tabs selector ── */}
      <View
        style={[
          styles.subTabBar,
          { backgroundColor: colors.background, borderBottomColor: colors.border },
        ]}
      >
        <SubTabButton
          label="Pendientes"
          badge={pendingSignals.filter((s) => s.status === "pending").length}
          active={activeTab === "pending"}
          onPress={() => setActiveTab("pending")}
          colors={colors}
        />
        <SubTabButton
          label="Cerradas"
          badge={0}
          active={activeTab === "closed"}
          onPress={() => setActiveTab("closed")}
          colors={colors}
        />
      </View>

      {/* ── Contenido: Pendientes ── */}
      {activeTab === "pending" && (
        <FlatList
          data={pendingSignals}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <SignalCard
              signal={item}
              onAccept={item.status === "pending" ? acceptSignal : undefined}
              onReject={item.status === "pending" ? rejectSignal : undefined}
            />
          )}
          contentContainerStyle={[
            styles.list,
            { paddingBottom: bottomPad + 100 },
          ]}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={loading}
              onRefresh={refresh}
              tintColor={colors.primary}
              colors={[colors.primary]}
            />
          }
          ListHeaderComponent={
            <View style={styles.listHeader}>
              <ApiErrorBanner />
            </View>
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <View
                style={[styles.emptyIcon, { backgroundColor: colors.card }]}
              >
                <Feather name="inbox" size={28} color={colors.mutedForeground} />
              </View>
              <Text style={[styles.emptyTitle, { color: colors.foreground }]}>
                Sin trades pendientes
              </Text>
              <Text
                style={[styles.emptyText, { color: colors.mutedForeground }]}
              >
                Las señales pendientes de acción y las posiciones abiertas
                aparecerán aquí
              </Text>
            </View>
          }
        />
      )}

      {/* ── Contenido: Cerradas ── */}
      {activeTab === "closed" && (
        <FlatList
          data={closedTrades}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <TradeCard trade={item} />}
          contentContainerStyle={[
            styles.list,
            { paddingBottom: bottomPad + 100 },
          ]}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={loading}
              onRefresh={refresh}
              tintColor={colors.primary}
              colors={[colors.primary]}
            />
          }
          ListHeaderComponent={
            <View style={styles.listHeader}>
              <ApiErrorBanner />
              {/* Sumario de estadísticas */}
              {closedTrades.length > 0 && (
                <View
                  style={[
                    styles.summaryCard,
                    {
                      backgroundColor: colors.card,
                      borderColor: colors.border,
                    },
                  ]}
                >
                  <SummaryItem
                    label="P&L Total"
                    value={`${totalPnL >= 0 ? "+" : ""}${totalPnL.toFixed(2)}€`}
                    color={totalPnL >= 0 ? colors.profit : colors.loss}
                    colors={colors}
                  />
                  <View
                    style={[styles.sep, { backgroundColor: colors.border }]}
                  />
                  <SummaryItem
                    label="Ganadas"
                    value={String(wins)}
                    color={colors.profit}
                    colors={colors}
                  />
                  <View
                    style={[styles.sep, { backgroundColor: colors.border }]}
                  />
                  <SummaryItem
                    label="Perdidas"
                    value={String(losses)}
                    color={colors.loss}
                    colors={colors}
                  />
                  <View
                    style={[styles.sep, { backgroundColor: colors.border }]}
                  />
                  <SummaryItem
                    label="P.Factor"
                    value={profitFactor}
                    color={
                      parseFloat(profitFactor) >= 1.5
                        ? colors.profit
                        : colors.foreground
                    }
                    colors={colors}
                  />
                </View>
              )}
            </View>
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <View
                style={[styles.emptyIcon, { backgroundColor: colors.card }]}
              >
                <Feather name="clock" size={28} color={colors.mutedForeground} />
              </View>
              <Text style={[styles.emptyTitle, { color: colors.foreground }]}>
                Sin operaciones cerradas
              </Text>
              <Text
                style={[styles.emptyText, { color: colors.mutedForeground }]}
              >
                Las operaciones que alcancen TP o SL aparecerán aquí
              </Text>
            </View>
          }
        />
      )}
    </View>
  );
}

// ── Sub-componentes ───────────────────────────────────────────────────────────

function SubTabButton({
  label,
  badge,
  active,
  onPress,
  colors,
}: {
  label: string;
  badge: number;
  active: boolean;
  onPress: () => void;
  colors: ReturnType<typeof useColors>;
}) {
  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.75}
      style={[
        styles.subTab,
        active && {
          borderBottomWidth: 2,
          borderBottomColor: colors.primary,
        },
      ]}
    >
      <View style={styles.subTabInner}>
        <Text
          style={[
            styles.subTabLabel,
            {
              color: active ? colors.primary : colors.mutedForeground,
              fontFamily: active ? "Inter_700Bold" : "Inter_500Medium",
            },
          ]}
        >
          {label}
        </Text>
        {badge > 0 && (
          <View
            style={[styles.subTabBadge, { backgroundColor: colors.pending }]}
          >
            <Text style={[styles.subTabBadgeText, { color: "#09090b" }]}>
              {badge}
            </Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );
}

function SummaryItem({
  label,
  value,
  color,
  colors,
}: {
  label: string;
  value: string;
  color: string;
  colors: ReturnType<typeof useColors>;
}) {
  return (
    <View style={styles.summaryItem}>
      <Text style={[styles.summaryValue, { color }]}>{value}</Text>
      <Text style={[styles.summaryLabel, { color: colors.mutedForeground }]}>
        {label}
      </Text>
    </View>
  );
}

// ── Estilos ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },

  // Sub-tab bar
  subTabBar: {
    flexDirection: "row",
    borderBottomWidth: 1,
  },
  subTab: {
    flex: 1,
    paddingVertical: 14,
    alignItems: "center",
  },
  subTabInner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  subTabLabel: {
    fontSize: 14,
  },
  subTabBadge: {
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 5,
  },
  subTabBadgeText: {
    fontSize: 11,
    fontFamily: "Inter_700Bold",
  },

  // Listas
  list: { paddingHorizontal: 16, paddingTop: 8 },
  listHeader: { marginBottom: 4 },

  // Sumario cerradas
  summaryCard: {
    borderRadius: 16,
    borderWidth: 1,
    flexDirection: "row",
    padding: 16,
    marginBottom: 12,
  },
  summaryItem: { flex: 1, alignItems: "center", gap: 4 },
  summaryValue: {
    fontSize: 16,
    fontFamily: "Inter_700Bold",
    fontVariant: ["tabular-nums"],
  },
  summaryLabel: {
    fontSize: 10,
    fontFamily: "Inter_500Medium",
    textTransform: "uppercase",
    letterSpacing: 0.4,
  },
  sep: { width: 1, marginVertical: 4 },

  // Empty states
  empty: { alignItems: "center", paddingTop: 60, gap: 12 },
  emptyIcon: {
    width: 60,
    height: 60,
    borderRadius: 30,
    alignItems: "center",
    justifyContent: "center",
  },
  emptyTitle: { fontSize: 18, fontFamily: "Inter_600SemiBold" },
  emptyText: {
    fontSize: 14,
    fontFamily: "Inter_400Regular",
    textAlign: "center",
    paddingHorizontal: 32,
  },
});
