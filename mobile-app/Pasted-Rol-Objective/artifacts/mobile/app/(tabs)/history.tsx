import React, { useMemo } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  Platform,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { useColors } from "@/hooks/useColors";
import { useTrading } from "@/context/TradingContext";
import { TradeCard } from "@/components/TradeCard";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";

export default function HistoryScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const { trades, dailyPnL } = useTrading();

  const sorted = useMemo(
    () => [...trades].sort((a, b) => new Date(b.closedAt).getTime() - new Date(a.closedAt).getTime()),
    [trades]
  );

  const wins = trades.filter((t) => t.profit > 0).length;
  const losses = trades.filter((t) => t.profit <= 0).length;
  const totalProfit = trades.filter((t) => t.profit > 0).reduce((s, t) => s + t.profit, 0);
  const totalLoss = Math.abs(trades.filter((t) => t.profit < 0).reduce((s, t) => s + t.profit, 0));
  const profitFactor = totalLoss > 0 ? (totalProfit / totalLoss).toFixed(2) : "∞";

  const topPad = Platform.OS === "web" ? 67 : insets.top;
  const bottomPad = Platform.OS === "web" ? 34 : 0;

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <FlatList
        data={sorted}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <TradeCard trade={item} />}
        contentContainerStyle={[
          styles.list,
          { paddingTop: topPad + 16, paddingBottom: bottomPad + 100 },
        ]}
        showsVerticalScrollIndicator={false}
        scrollEnabled={!!sorted.length}
        ListHeaderComponent={
          <View style={styles.headerSection}>
            <ApiErrorBanner />
            <Text style={[styles.title, { color: colors.foreground }]}>Historial</Text>
            <Text style={[styles.subtitle, { color: colors.mutedForeground }]}>
              {trades.length} operaciones cerradas
            </Text>

            <View style={[styles.summaryCard, { backgroundColor: colors.card, borderColor: colors.border }]}>
              <SummaryItem
                label="P&L Total"
                value={`${dailyPnL >= 0 ? "+" : ""}${dailyPnL.toFixed(2)}€`}
                color={dailyPnL >= 0 ? colors.profit : colors.loss}
                colors={colors}
              />
              <View style={[styles.sep, { backgroundColor: colors.border }]} />
              <SummaryItem
                label="Ganadas"
                value={String(wins)}
                color={colors.profit}
                colors={colors}
              />
              <View style={[styles.sep, { backgroundColor: colors.border }]} />
              <SummaryItem
                label="Perdidas"
                value={String(losses)}
                color={colors.loss}
                colors={colors}
              />
              <View style={[styles.sep, { backgroundColor: colors.border }]} />
              <SummaryItem
                label="P.Factor"
                value={profitFactor}
                color={parseFloat(profitFactor) >= 1.5 ? colors.profit : colors.foreground}
                colors={colors}
              />
            </View>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <View style={[styles.emptyIcon, { backgroundColor: colors.card }]}>
              <Feather name="clock" size={28} color={colors.mutedForeground} />
            </View>
            <Text style={[styles.emptyTitle, { color: colors.foreground }]}>Sin historial</Text>
            <Text style={[styles.emptyText, { color: colors.mutedForeground }]}>
              Las operaciones cerradas aparecerán aquí
            </Text>
          </View>
        }
      />
    </View>
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
      <Text style={[styles.summaryLabel, { color: colors.mutedForeground }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: { paddingHorizontal: 16, gap: 0 },
  headerSection: { gap: 6, marginBottom: 16 },
  title: { fontSize: 28, fontFamily: "Inter_700Bold" },
  subtitle: { fontSize: 13, fontFamily: "Inter_400Regular" },
  summaryCard: {
    borderRadius: 16,
    borderWidth: 1,
    flexDirection: "row",
    padding: 16,
    marginTop: 10,
  },
  summaryItem: { flex: 1, alignItems: "center", gap: 4 },
  summaryValue: {
    fontSize: 16,
    fontFamily: "Inter_700Bold",
    fontVariant: ["tabular-nums"],
  },
  summaryLabel: { fontSize: 10, fontFamily: "Inter_500Medium", textTransform: "uppercase", letterSpacing: 0.4 },
  sep: { width: 1, marginVertical: 4 },
  empty: { alignItems: "center", paddingTop: 60, gap: 12 },
  emptyIcon: {
    width: 60,
    height: 60,
    borderRadius: 30,
    alignItems: "center",
    justifyContent: "center",
  },
  emptyTitle: { fontSize: 18, fontFamily: "Inter_600SemiBold" },
  emptyText: { fontSize: 14, fontFamily: "Inter_400Regular", textAlign: "center" },
});
