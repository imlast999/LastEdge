/**
 * Lab Screen — LastEdge Research Lab
 * 
 * Consolidates investigation modes and research runs.
 * Three investigation types:
 * - Quick Validation: Backtest only
 * - LastEdge Protocol: Backtest → Walk Forward → Monte Carlo → Exit Research
 * - Custom Investigation: Manual selection of phases
 */
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
import { useRouter } from "expo-router";
import { Feather } from "@expo/vector-icons";

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

export default function LabScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { t } = useTranslation();
  const { apiOverrides } = useSettings();

  const [runs, setRuns] = useState<ExitResearchRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<ExitResearchDetail | null>(null);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const topPad = insets.top;
  const bottomPad = insets.bottom + 120;

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

  const handleOpenSettings = () => {
    router.push("/settings-modal");
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={[
        styles.content,
        { paddingTop: 16, paddingBottom: bottomPad + 16 },
      ]}
      showsVerticalScrollIndicator={false}
    >
      <ApiErrorBanner />

      {/* Header with Settings Button - respects safe area */}
      <View style={[styles.headerContainer, { paddingTop: insets.top }]}>
        <View style={styles.headerContent}>
          <Text style={[styles.title, { color: colors.foreground }]}>LastEdge Research Lab</Text>
          <Text style={[styles.subtitle, { color: colors.mutedForeground }]}>
            Quantitative strategy validation
          </Text>
        </View>
        <TouchableOpacity
          onPress={handleOpenSettings}
          style={[styles.settingsButton, { backgroundColor: colors.secondary }]}
        >
          <Feather name="settings" size={20} color={colors.foreground} />
        </TouchableOpacity>
      </View>

      {/* Investigation Modes */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.mutedForeground }]}>Investigation Modes</Text>
        <View style={styles.modesGrid}>
          <InvestigationMode
            title="Quick Validation"
            description="Fast historical validation"
            icon="zap"
            color="#3b82f6"
            colors={colors}
            onPress={() => {}} // TODO: Wire to actual investigation launch
          />
          <InvestigationMode
            title="LastEdge Protocol"
            description="Complete quantitative validation"
            icon="layers"
            color="#10b981"
            colors={colors}
            onPress={() => {}} // TODO: Wire to actual investigation launch
          />
          <InvestigationMode
            title="Custom Investigation"
            description="Manual phase selection"
            icon="sliders"
            color="#f59e0b"
            colors={colors}
            onPress={() => {}} // TODO: Wire to actual investigation launch
          />
        </View>
      </View>

      {/* Investigations List */}
      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.mutedForeground }]}>Investigations</Text>

        <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}>
          {loadingRuns ? (
            <ActivityIndicator color={colors.primary} />
          ) : runs.length === 0 ? (
            <View style={styles.emptyState}>
              <Feather name="inbox" size={32} color={colors.mutedForeground} />
              <Text style={[styles.emptyTitle, { color: colors.foreground }]}>
                No investigations yet
              </Text>
              <Text style={[styles.emptyText, { color: colors.mutedForeground }]}>
                Start by selecting an investigation mode
              </Text>
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
                    {
                      color: run.run_id === selectedRunId ? colors.primaryForeground : colors.foreground,
                    },
                  ]}
                >
                  {run.symbol} · {run.variant_count} variants
                </Text>
                <Text
                  style={[
                    styles.runItemSubtitle,
                    {
                      color:
                        run.run_id === selectedRunId ? colors.primaryForeground : colors.mutedForeground,
                    },
                  ]}
                >
                  {new Date(run.generated_at).toLocaleDateString()} · {run.best_variant ?? "All"}
                </Text>
              </TouchableOpacity>
            ))
          )}
        </View>
      </View>

      {/* Run Detail */}
      {selectedRun ? (
        <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}>
          <View style={styles.cardHeader}>
            <Text style={[styles.cardTitle, { color: colors.foreground }]}>Investigation Detail</Text>
            {selectedSummary ? (
              <Text
                style={[styles.pill, { backgroundColor: colors.primary, color: colors.primaryForeground }]}
              >
                {selectedSummary.best_variant ?? "–"}
              </Text>
            ) : null}
          </View>

          <StatRow label="Investigation ID" value={selectedRun.run_id} colors={colors} />
          <StatRow label="Symbol" value={selectedRun.symbol} colors={colors} />
          <StatRow
            label="Generated"
            value={new Date(selectedRun.generated_at).toLocaleString()}
            colors={colors}
          />
          <StatRow label="Variants" value={String(selectedRun.variant_count)} colors={colors} />

          <View style={styles.sectionDivider} />
          <Text style={[styles.sectionLabel, { color: colors.mutedForeground }]}>Conclusions</Text>
          <View style={styles.conclusionsGrid}>
            <StatRow
              label="Most Robust"
              value={selectedRun.conclusions?.most_robust ?? "–"}
              colors={colors}
            />
            <StatRow
              label="Lowest Ruin"
              value={selectedRun.conclusions?.lowest_ruin_probability ?? "–"}
              colors={colors}
            />
            <StatRow
              label="Lowest DD"
              value={selectedRun.conclusions?.lowest_drawdown ?? "–"}
              colors={colors}
            />
            <StatRow
              label="Highest PF"
              value={selectedRun.conclusions?.highest_profit ?? "–"}
              colors={colors}
            />
          </View>

          <View style={styles.sectionDivider} />
          <Text style={[styles.sectionLabel, { color: colors.mutedForeground }]}>All Variants</Text>
          {selectedRun.comparison.length > 0 ? (
            selectedRun.comparison.slice(0, 4).map((variant) => (
              <VariantRow key={variant.variant} variant={variant} colors={colors} />
            ))
          ) : (
            <Text style={[styles.emptyText, { color: colors.mutedForeground }]}>No variants</Text>
          )}
          {selectedRun.comparison.length > 4 ? (
            <Text style={[styles.moreText, { color: colors.mutedForeground }]}>
              +{selectedRun.comparison.length - 4} more variants
            </Text>
          ) : null}
        </View>
      ) : loadingDetail ? (
        <ActivityIndicator color={colors.primary} />
      ) : null}

      {error ? (
        <Text style={[styles.errorText, { color: colors.destructive }]}>{error}</Text>
      ) : null}
    </ScrollView>
  );
}

function InvestigationMode({
  title,
  description,
  icon,
  color,
  colors,
  onPress,
}: {
  title: string;
  description: string;
  icon: any;
  color: string;
  colors: ReturnType<typeof useColors>;
  onPress: () => void;
}) {
  return (
    <TouchableOpacity
      onPress={onPress}
      style={[styles.modeCard, { backgroundColor: colors.secondary, borderColor: colors.border }]}
    >
      <View style={[styles.modeIcon, { backgroundColor: color }]}>
        <Feather name={icon} size={24} color="white" />
      </View>
      <Text style={[styles.modeTitle, { color: colors.foreground }]}>{title}</Text>
      <Text style={[styles.modeDescription, { color: colors.mutedForeground }]}>{description}</Text>
    </TouchableOpacity>
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
          PF: {variant.profit_factor.toFixed(2)}
        </Text>
        <Text style={[styles.variantStat, { color: colors.mutedForeground }]}>
          WR: {variant.winrate.toFixed(1)}%
        </Text>
        <Text style={[styles.variantStat, { color: colors.mutedForeground }]}>
          DD: {variant.max_drawdown.toFixed(0)}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingHorizontal: 16, gap: 16 },
  headerContainer: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 4,
    gap: 12,
    paddingHorizontal: 0,
  },
  headerContent: { flex: 1 },
  title: { fontSize: 28, fontFamily: "Inter_700Bold" },
  subtitle: { fontSize: 13, fontFamily: "Inter_400Regular", marginTop: 2 },
  settingsButton: {
    width: 40,
    height: 40,
    borderRadius: 8,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 2,
  },
  section: { gap: 12 },
  sectionTitle: {
    fontSize: 11,
    fontFamily: "Inter_600SemiBold",
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },
  modesGrid: { gap: 12 },
  modeCard: {
    borderRadius: 14,
    borderWidth: 1,
    padding: 16,
    gap: 8,
    alignItems: "center",
  },
  modeIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 4,
  },
  modeTitle: { fontSize: 15, fontFamily: "Inter_600SemiBold", textAlign: "center" },
  modeDescription: { fontSize: 12, fontFamily: "Inter_400Regular", textAlign: "center" },
  card: { borderRadius: 16, borderWidth: 1, padding: 16, gap: 12 },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 12,
  },
  cardTitle: { fontSize: 16, fontFamily: "Inter_600SemiBold" },
  sectionLabel: {
    fontSize: 11,
    fontFamily: "Inter_600SemiBold",
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },
  emptyState: { gap: 12, paddingVertical: 24, alignItems: "center" },
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
  conclusionsGrid: { gap: 8 },
  statRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  statLabel: { fontSize: 12, fontFamily: "Inter_400Regular" },
  statValue: { fontSize: 12, fontFamily: "Inter_600SemiBold", fontVariant: ["tabular-nums"] },
  variantRow: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginTop: 8,
    gap: 8,
  },
  variantTitle: { fontSize: 13, fontFamily: "Inter_600SemiBold" },
  variantStats: { gap: 4 },
  variantStat: { fontSize: 11, fontFamily: "Inter_400Regular" },
  moreText: { fontSize: 12, fontFamily: "Inter_400Regular", fontStyle: "italic", marginTop: 8 },
  errorText: { fontSize: 12, fontFamily: "Inter_400Regular" },
});
