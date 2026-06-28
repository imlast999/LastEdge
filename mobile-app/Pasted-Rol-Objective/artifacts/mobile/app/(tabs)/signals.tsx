import React, { useState } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  Platform,
  TouchableOpacity,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";
import { useColors } from "@/hooks/useColors";
import { useTrading } from "@/context/TradingContext";
import { SignalCard } from "@/components/SignalCard";
import type { Signal } from "@/context/TradingContext";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";

type FilterTab = "all" | "pending" | "active" | "rejected";

const FILTERS: { key: FilterTab; label: string }[] = [
  { key: "all", label: "Todas" },
  { key: "pending", label: "Pendientes" },
  { key: "active", label: "Activas" },
  { key: "rejected", label: "Rechazadas" },
];

export default function SignalsScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const { signals, acceptSignal, rejectSignal, pendingSignals } = useTrading();
  const [filter, setFilter] = useState<FilterTab>("all");

  const filtered = signals.filter((s) => filter === "all" || s.status === filter);

  const topPad = Platform.OS === "web" ? 67 : insets.top;
  const bottomPad = Platform.OS === "web" ? 34 : 0;

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={[styles.header, { paddingTop: topPad + 16 }]}>
        <ApiErrorBanner />
        <View style={styles.titleRow}>
          <Text style={[styles.title, { color: colors.foreground }]}>Señales</Text>
          {pendingSignals > 0 && (
            <View style={[styles.badge, { backgroundColor: colors.pending }]}>
              <Text style={[styles.badgeText, { color: "#09090b" }]}>{pendingSignals}</Text>
            </View>
          )}
        </View>
        <Text style={[styles.subtitle, { color: colors.mutedForeground }]}>
          {signals.length} señales registradas
        </Text>

        <View style={styles.filterRow}>
          {FILTERS.map((f) => {
            const count = f.key === "all" ? signals.length : signals.filter((s) => s.status === f.key).length;
            const active = filter === f.key;
            return (
              <TouchableOpacity
                key={f.key}
                onPress={() => setFilter(f.key)}
                style={[
                  styles.filterBtn,
                  {
                    backgroundColor: active ? colors.primary : colors.card,
                    borderColor: active ? colors.primary : colors.border,
                  },
                ]}
                activeOpacity={0.75}
              >
                <Text
                  style={[
                    styles.filterText,
                    { color: active ? colors.primaryForeground : colors.mutedForeground },
                  ]}
                >
                  {f.label}
                </Text>
                {count > 0 && (
                  <Text
                    style={[
                      styles.filterCount,
                      { color: active ? colors.primaryForeground : colors.mutedForeground },
                    ]}
                  >
                    {count}
                  </Text>
                )}
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      <FlatList
        data={filtered}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <SignalCard
            signal={item}
            onAccept={acceptSignal}
            onReject={rejectSignal}
          />
        )}
        contentContainerStyle={[
          styles.list,
          { paddingBottom: bottomPad + 100 },
        ]}
        showsVerticalScrollIndicator={false}
        scrollEnabled={!!filtered.length}
        ListEmptyComponent={
          <View style={styles.empty}>
            <View style={[styles.emptyIcon, { backgroundColor: colors.card }]}>
              <Feather name="inbox" size={28} color={colors.mutedForeground} />
            </View>
            <Text style={[styles.emptyTitle, { color: colors.foreground }]}>
              Sin señales
            </Text>
            <Text style={[styles.emptyText, { color: colors.mutedForeground }]}>
              No hay señales {filter !== "all" ? `con estado "${filter}"` : "registradas"} aún
            </Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    paddingHorizontal: 16,
    paddingBottom: 12,
    gap: 6,
  },
  titleRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  title: { fontSize: 28, fontFamily: "Inter_700Bold" },
  badge: {
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 6,
  },
  badgeText: { fontSize: 12, fontFamily: "Inter_700Bold" },
  subtitle: { fontSize: 13, fontFamily: "Inter_400Regular" },
  filterRow: { flexDirection: "row", gap: 8, marginTop: 8 },
  filterBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1,
  },
  filterText: { fontSize: 12, fontFamily: "Inter_600SemiBold" },
  filterCount: { fontSize: 11, fontFamily: "Inter_500Medium" },
  list: { paddingHorizontal: 16, paddingTop: 8 },
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
