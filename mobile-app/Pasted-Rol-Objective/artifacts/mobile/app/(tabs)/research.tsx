import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Platform,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useColors } from "@/hooks/useColors";
import { useSettings } from "@/context/SettingsContext";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { useTranslation } from "@/hooks/useTranslation";
import {
  listExitResearchRuns,
  fetchExitResearchDetail,
  type ExitResearchRun,
  type ExitResearchDetail,
  type ExitVariant,
} from "@/services/researchApi";

export default function ResearchScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const { t } = useTranslation();
  const { apiOverrides } = useSettings();

  const [runs, setRuns] = useState<ExitResearchRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<ExitResearchDetail | null>(null);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const topPad = Platform.OS === "web" ? 67 : insets.top;
  const bottomPad = Platform.OS === "web" ? 34 : 0;

  const selectedSummary = runs.find((run) => run.run_id === selectedRunId);

  const loadRuns = useCallback(async () => {
    setError(null);
    setLoadingRuns(true);
    try {
      const data = await listExitResearchRuns(apiOverrides);
      setRuns(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setRuns([]);
    } finally {
      setLoadingRuns(false);
    }
  }, [apiOverrides]);

  const loadDetail = useCallback(
    async (runId: string) => {
      setError(null);
      setLoadingDetail(true);
      try {
        const detail = await fetchExitResearchDetail(runId, apiOverrides);
        setSelectedRun(detail);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoadingDetail(false);
      }
    },
    [apiOverrides]
  );

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    if (!selectedRunId && runs.length > 0) {
      const firstRunId = runs[0].run_id;
      setSelectedRunId(firstRunId);
      loadDetail(firstRunId);
    }
  }, [runs, selectedRunId, loadDetail]);

  const handleSelectRun = (run: ExitResearchRun) => {
    setSelectedRunId(run.run_id);
    setSelectedRun(null);
    loadDetail(run.run_id);
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={[
        styles.content,
        { paddingTop: topPad + 16, paddingBottom: bottomPad + 100 },
      ]}
      showsVerticalScrollIndicator={false}
    >
      <ApiErrorBanner />

      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.foreground }]}>{t("exitResearch")}</Text>
        <Text style={[styles.subtitle, { color: colors.mutedForeground }]}>{t("researchTitle")}</Text>
      </View>

      <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}> 
        <Text style={[styles.sectionLabel, { color: colors.mutedForeground }]}>{t("selectRun")}</Text>

        {loadingRuns ? (
          <ActivityIndicator color={colors.primary} />
        ) : runs.length === 0 ? (
          <View style={styles.emptyState}>
            <Text style={[styles.emptyTitle, { color: colors.foreground }]}>{t("noResearchRuns")}</Text>
            <Text style={[styles.emptyText, { color: colors.mutedForeground }]}>{t("noResearchDesc")}</Text>
          </View>
        ) : (
          runs.map((run) => (
            <TouchableOpacity
              key={run.run_id}
              onPress={() => handleSelectRun(run)}
              style={[
                styles.runItem,
                {
                  backgroundColor:
                    run.run_id === selectedRunId ? colors.primary : colors.secondary,
                  borderColor: colors.border,
                },
              ]}
            >
              <Text
                style={[
                  styles.runItemTitle,
                  { color: run.run_id === selectedRunId ? colors.primaryForeground : colors.foreground },
                ]}
              >
                {run.symbol} · {run.variant_count} {t("variantCount")}
              </Text>
              <Text
                style={[
                  styles.runItemSubtitle,
                  { color: run.run_id === selectedRunId ? colors.primaryForeground : colors.mutedForeground },
                ]}
              >
                {new Date(run.generated_at).toLocaleDateString()} · {run.best_variant ?? t("showAll")}
              </Text>
            </TouchableOpacity>
          ))
        )}
      </View>

      {selectedRun ? (
        <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}> 
          <View style={styles.cardHeader}>
            <Text style={[styles.cardTitle, { color: colors.foreground }]}>{t("runDetail")}</Text>
            {selectedSummary ? (
              <Text style={[styles.pill, { backgroundColor: colors.primary, color: colors.primaryForeground }]}>
                {selectedSummary.best_variant ?? "–"}
              </Text>
            ) : null}
          </View>

          <StatRow label={t("runId")} value={selectedRun.run_id} colors={colors} />
          <StatRow label={t("symbol")} value={selectedRun.symbol} colors={colors} />
          <StatRow
            label={t("generatedAt")}
            value={new Date(selectedRun.generated_at).toLocaleString()}
            colors={colors}
          />
          <StatRow
            label={t("variantCount")}
            value={String(selectedRun.variant_count)}
            colors={colors}
          />

          <View style={styles.sectionDivider} />
          <Text style={[styles.sectionLabel, { color: colors.mutedForeground }]}>{t("conclusions")}</Text>
          <View style={styles.conclusionsGrid}>
            <StatRow
              label={t("mostRobust")}
              value={selectedRun.conclusions?.most_robust ?? "–"}
              colors={colors}
            />
            <StatRow
              label={t("lowestRuin")}
              value={selectedRun.conclusions?.lowest_ruin_probability ?? "–"}
              colors={colors}
            />
            <StatRow
              label={t("lowestDD")}
              value={selectedRun.conclusions?.lowest_drawdown ?? "–"}
              colors={colors}
            />
            <StatRow
              label={t("highestPF")}
              value={selectedRun.conclusions?.highest_profit ?? "–"}
              colors={colors}
            />
          </View>

          <View style={styles.sectionDivider} />
          <Text style={[styles.sectionLabel, { color: colors.mutedForeground }]}>{t("allVariants")}</Text>
          {selectedRun.comparison.length > 0 ? (
            selectedRun.comparison.slice(0, 4).map((variant) => (
              <VariantRow key={variant.variant} variant={variant} colors={colors} />
            ))
          ) : (
            <Text style={[styles.emptyText, { color: colors.mutedForeground }]}>{t("unknownError")}</Text>
          )}
          {selectedRun.comparison.length > 4 ? (
            <Text style={[styles.moreText, { color: colors.mutedForeground }]}>+{selectedRun.comparison.length - 4} more variants</Text>
          ) : null}
        </View>
      ) : loadingDetail ? (
        <ActivityIndicator color={colors.primary} />
      ) : null}

      {error ? <Text style={[styles.errorText, { color: colors.destructive }]}>{error}</Text> : null}
    </ScrollView>
  );
}

function StatRow({
  label,
  value,
  colors,
}: {
  label: string;
  value: string;
  colors: ReturnType<typeof useColors>;
}) {
  return (
    <View style={styles.statRow}>
      <Text style={[styles.statLabel, { color: colors.mutedForeground }]}>{label}</Text>
      <Text style={[styles.statValue, { color: colors.foreground }]}>{value}</Text>
    </View>
  );
}

function VariantRow({
  variant,
  colors,
}: {
  variant: ExitVariant;
  colors: ReturnType<typeof useColors>;
}) {
  const { t } = useTranslation();

  return (
    <View style={[styles.variantRow, { borderColor: colors.border, backgroundColor: colors.secondary }]}> 
      <Text style={[styles.variantTitle, { color: colors.foreground }]}>{variant.variant}</Text>
      <View style={styles.variantStats}>
        <Text style={[styles.variantStat, { color: colors.mutedForeground }]}>
          {t("profitFactor")}: {variant.profit_factor.toFixed(2)}
        </Text>
        <Text style={[styles.variantStat, { color: colors.mutedForeground }]}>
          {t("winRate")}: {variant.winrate.toFixed(1)}%
        </Text>
        <Text style={[styles.variantStat, { color: colors.mutedForeground }]}>
          {t("drawdown")}: {variant.max_drawdown.toFixed(0)}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingHorizontal: 16, gap: 16 },
  header: { marginBottom: 4 },
  title: { fontSize: 28, fontFamily: "Inter_700Bold" },
  subtitle: { fontSize: 13, fontFamily: "Inter_400Regular", marginTop: 2 },
  card: { borderRadius: 16, borderWidth: 1, padding: 16, gap: 12 },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12 },
  cardTitle: { fontSize: 16, fontFamily: "Inter_600SemiBold" },
  sectionLabel: {
    fontSize: 11,
    fontFamily: "Inter_600SemiBold",
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },
  emptyState: { gap: 8, paddingVertical: 12 },
  emptyTitle: { fontSize: 16, fontFamily: "Inter_600SemiBold" },
  emptyText: { fontSize: 13, fontFamily: "Inter_400Regular" },
  runItem: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    marginTop: 10,
  },
  runItemTitle: { fontSize: 14, fontFamily: "Inter_600SemiBold" },
  runItemSubtitle: { fontSize: 12, fontFamily: "Inter_400Regular", marginTop: 6 },
  pill: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    fontFamily: "Inter_600SemiBold",
    fontSize: 11,
  },
  sectionDivider: { borderBottomWidth: 1, opacity: 0.2, marginVertical: 10 },
  conclusionsGrid: { gap: 10 },
  statRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  statLabel: { fontSize: 13, fontFamily: "Inter_400Regular" },
  statValue: { fontSize: 13, fontFamily: "Inter_600SemiBold" },
  variantRow: { borderWidth: 1, borderRadius: 14, padding: 14, marginTop: 10 },
  variantTitle: { fontSize: 14, fontFamily: "Inter_600SemiBold" },
  variantStats: { marginTop: 8, gap: 4 },
  variantStat: { fontSize: 12, fontFamily: "Inter_400Regular" },
  moreText: { fontSize: 12, fontFamily: "Inter_400Regular", marginTop: 10 },
  errorText: { fontSize: 13, fontFamily: "Inter_500Medium" },
});
