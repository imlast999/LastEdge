/**
 * Research Screen — Exit Research Dashboard (Fase 1)
 *
 * Pantalla principal de investigación cuantitativa de LastEdge.
 * Muestra todos los runs de Exit Research disponibles y permite
 * explorar las variantes de cada uno con sus métricas completas.
 *
 * Flujo:
 *   1. Lista de runs (RunListView)
 *   2. Detalle de un run: tabla comparativa de variantes (RunDetailView)
 *   3. Detalle de una variante: MAE/MFE, degradación, WF/MC (VariantDetailView)
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";

import { useColors } from "@/hooks/useColors";
import { useTranslation } from "@/hooks/useTranslation";
import { useSettings } from "@/context/SettingsContext";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { InteractiveEquityChart, EquityCurveHeader } from "@/components/InteractiveEquityChart";
import { ResearchTradeCard } from "@/components/ResearchTradeCard";
import {
  listExitResearchRuns,
  fetchExitResearchDetail,
  fetchEquityCurve,
  fetchVariantTrades,
  type ExitResearchRun,
  type ExitResearchDetail,
  type ExitVariant,
  type EquityCurveData,
  type ResearchTrade,
  type TradePageStats,
} from "@/services/researchApi";

// ── Tipos de ordenación ───────────────────────────────────────────────────────
type SortKey = "stability_score" | "profit_factor" | "winrate" | "max_drawdown" | "total_pips";
type FilterKey = "all" | "positive";

// ── Colores semánticos para badges ────────────────────────────────────────────
function wfColor(wf: string | null, colors: ReturnType<typeof useColors>): string {
  switch (wf) {
    case "STABLE":     return colors.profit;
    case "MARGINAL":   return colors.pending;
    case "UNSTABLE":   return colors.loss;
    case "OVERFITTED": return "#f97316"; // orange
    default:           return colors.mutedForeground;
  }
}

function pfColor(pf: number, colors: ReturnType<typeof useColors>): string {
  if (pf >= 1.5) return colors.profit;
  if (pf >= 1.0) return colors.pending;
  return colors.loss;
}

function stabilityColor(score: number, colors: ReturnType<typeof useColors>): string {
  if (score >= 40) return colors.profit;
  if (score >= 10) return colors.pending;
  return colors.mutedForeground;
}

// ── Formateo ──────────────────────────────────────────────────────────────────
const fmt  = (v: number | null | undefined, d = 2) =>
  v == null ? "—" : v.toFixed(d);
const fmtPct = (v: number | null | undefined) =>
  v == null ? "—" : `${v.toFixed(1)}%`;
const fmtPips = (v: number | null | undefined) => {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(0)}`;
};

// ═════════════════════════════════════════════════════════════════════════════
// PANTALLA PRINCIPAL
// ═════════════════════════════════════════════════════════════════════════════

export default function ResearchScreen() {
  const colors  = useColors();
  const insets  = useSafeAreaInsets();
  const { t }   = useTranslation();
  const { apiOverrides } = useSettings();

  // ── Vista activa: lista de runs → detalle run → detalle variante ──────────
  const [view, setView] = useState<"list" | "detail" | "variant">("list");

  // ── Estado de datos ───────────────────────────────────────────────────────
  const [runs, setRuns]           = useState<ExitResearchRun[]>([]);
  const [detail, setDetail]       = useState<ExitResearchDetail | null>(null);
  const [activeVariant, setActiveVariant] = useState<ExitVariant | null>(null);
  const [activeRunId, setActiveRunId]     = useState<string | null>(null);
  const [equityCurve, setEquityCurve]     = useState<EquityCurveData | null>(null);
  const [loadingCurve, setLoadingCurve]   = useState(false);
  const [trades, setTrades]               = useState<ResearchTrade[]>([]);
  const [tradesStats, setTradesStats]     = useState<TradePageStats | null>(null);
  const [tradesTotal, setTradesTotal]     = useState(0);
  const [tradesPage, setTradesPage]       = useState(0);
  const [tradesHasMore, setTradesHasMore] = useState(false);
  const [loadingTrades, setLoadingTrades] = useState(false);
  const [tradesFilter, setTradesFilter]   = useState<"ALL" | "WIN" | "LOSS">("ALL");

  // ── Estado de UI ──────────────────────────────────────────────────────────
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [sortKey, setSortKey]     = useState<SortKey>("stability_score");
  const [filter, setFilter]       = useState<FilterKey>("all");

  const bottomPad = Platform.OS === "web" ? 34 : 0;

  // ── Carga inicial de la lista ─────────────────────────────────────────────
  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listExitResearchRuns(apiOverrides);
      setRuns(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [apiOverrides]);

  useEffect(() => { loadRuns(); }, [loadRuns]);

  // ── Carga del detalle de un run ────────────────────────────────────────────
  const openRun = useCallback(async (run: ExitResearchRun) => {
    setLoading(true);
    setError(null);
    setEquityCurve(null);
    try {
      const data = await fetchExitResearchDetail(run.run_id, apiOverrides);
      setDetail(data);
      setActiveRunId(run.run_id);
      setView("detail");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [apiOverrides]);

  // ── Carga de la equity curve para una variante ────────────────────────────
  const loadEquityCurve = useCallback(async (runId: string, variantName: string) => {    setLoadingCurve(true);
    setEquityCurve(null);
    try {
      // Decimación automática: si hay muchos trades, reducir a cada 3
      const data = await fetchEquityCurve(runId, variantName, 1, apiOverrides);
      // Si el payload supera 2000 puntos, decimar
      if (data.points.length > 2000) {
        const step = Math.ceil(data.points.length / 1000);
        const decimated = await fetchEquityCurve(runId, variantName, step, apiOverrides);
        setEquityCurve(decimated);
      } else {
        setEquityCurve(data);
      }
    } catch {
      setEquityCurve(null); // silencioso — la sección simplemente no aparece
    } finally {
      setLoadingCurve(false);
    }
  }, [apiOverrides]);

  // ── Carga de trades paginada ──────────────────────────────────────────────
  const loadTrades = useCallback(async (
    runId: string,
    variantName: string,
    page: number,
    filter: "ALL" | "WIN" | "LOSS",
    reset = false,
  ) => {
    setLoadingTrades(true);
    try {
      const result = filter === "ALL"
        ? await fetchVariantTrades(runId, variantName, { page, limit: 50, overrides: apiOverrides })
        : await fetchVariantTrades(runId, variantName, { page, limit: 50, result: filter as "WIN" | "LOSS", overrides: apiOverrides });
      setTrades(prev => reset ? result.trades : [...prev, ...result.trades]);
      setTradesStats(result.stats);
      setTradesTotal(result.total);
      setTradesPage(result.page);
      setTradesHasMore(result.has_more);
    } catch {
      // silencioso
    } finally {
      setLoadingTrades(false);
    }
  }, [apiOverrides]);

  // ── Variantes ordenadas y filtradas ──────────────────────────────────────
  const sortedVariants = useMemo(() => {
    if (!detail) return [];
    let list = [...detail.comparison];
    if (filter === "positive") list = list.filter(v => v.profit_factor >= 1.0);
    list.sort((a, b) => {
      switch (sortKey) {
        case "profit_factor":   return b.profit_factor - a.profit_factor;
        case "winrate":         return b.winrate - a.winrate;
        case "max_drawdown":    return a.max_drawdown - b.max_drawdown;
        case "total_pips":      return b.total_pips - a.total_pips;
        default:                return b.stability_score - a.stability_score;
      }
    });
    return list;
  }, [detail, sortKey, filter]);

  // ── Navegación hacia atrás ────────────────────────────────────────────────
  const goBack = () => {
    if (view === "variant") { setActiveVariant(null); setView("detail"); }
    else                    { setDetail(null); setView("list"); }
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      {/* Header interno con breadcrumb */}
      {view !== "list" && (
        <TouchableOpacity
          onPress={goBack}
          style={[styles.backBar, { borderBottomColor: colors.border, backgroundColor: colors.background }]}
          activeOpacity={0.7}
        >
          <Feather name="arrow-left" size={18} color={colors.primary} />
          <Text style={[styles.backText, { color: colors.primary }]}>
            {view === "detail"
              ? t("exitResearch")
              : `${detail?.symbol ?? ""} · ${detail?.run_id ?? ""}`}
          </Text>
        </TouchableOpacity>
      )}

      {/* Contenido principal según vista activa */}
      {view === "list" && (
        <RunListView
          runs={runs}
          loading={loading}
          error={error}
          colors={colors}
          t={t}
          insets={insets}
          bottomPad={bottomPad}
          onSelectRun={openRun}
          onRefresh={loadRuns}
        />
      )}

      {view === "detail" && detail && (
        <RunDetailView
          detail={detail}
          sortedVariants={sortedVariants}
          sortKey={sortKey}
          filter={filter}
          loading={loading}
          colors={colors}
          t={t}
          bottomPad={bottomPad}
          onSortChange={setSortKey}
          onFilterChange={setFilter}
          onSelectVariant={(v) => {
            setActiveVariant(v);
            setEquityCurve(null);
            setTrades([]);
            setTradesStats(null);
            setTradesTotal(0);
            setTradesPage(0);
            setTradesHasMore(false);
            setTradesFilter("ALL");
            setView("variant");
            if (activeRunId) {
              loadEquityCurve(activeRunId, v.variant);
              loadTrades(activeRunId, v.variant, 0, "ALL", true);
            }
          }}
        />
      )}

      {view === "variant" && activeVariant && detail && (
        <VariantDetailView
          variant={activeVariant}
          symbol={detail.symbol}
          runId={activeRunId ?? ""}
          equityCurve={equityCurve}
          loadingCurve={loadingCurve}
          onLoadCurve={() => activeRunId && loadEquityCurve(activeRunId, activeVariant.variant)}
          trades={trades}
          tradesStats={tradesStats}
          tradesTotal={tradesTotal}
          tradesHasMore={tradesHasMore}
          loadingTrades={loadingTrades}
          tradesFilter={tradesFilter}
          onFilterChange={(f) => {
            setTradesFilter(f);
            setTrades([]);
            if (activeRunId) loadTrades(activeRunId, activeVariant.variant, 0, f, true);
          }}
          onLoadMoreTrades={() => {
            if (activeRunId && tradesHasMore && !loadingTrades)
              loadTrades(activeRunId, activeVariant.variant, tradesPage + 1, tradesFilter);
          }}
          colors={colors}
          t={t}
          bottomPad={bottomPad}
        />
      )}
    </View>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// VISTA 1 — LISTA DE RUNS
// ═════════════════════════════════════════════════════════════════════════════

function RunListView({
  runs, loading, error, colors, t, insets, bottomPad, onSelectRun, onRefresh,
}: {
  runs: ExitResearchRun[];
  loading: boolean;
  error: string | null;
  colors: ReturnType<typeof useColors>;
  t: (k: string) => string;
  insets: { top: number };
  bottomPad: number;
  onSelectRun: (r: ExitResearchRun) => void;
  onRefresh: () => void;
}) {
  const topPad = Platform.OS === "web" ? 67 : insets.top;

  return (
    <ScrollView
      style={{ flex: 1 }}
      contentContainerStyle={{ paddingTop: topPad + 16, paddingBottom: bottomPad + 100, paddingHorizontal: 16, gap: 12 }}
      showsVerticalScrollIndicator={false}
    >
      <ApiErrorBanner />

      {/* Cabecera */}
      <View style={styles.listHeader}>
        <View>
          <Text style={[styles.screenTitle, { color: colors.foreground }]}>{t("exitResearch")}</Text>
          <Text style={[styles.screenSubtitle, { color: colors.mutedForeground }]}>
            {runs.length > 0
              ? `${runs.length} run${runs.length !== 1 ? "s" : ""} disponibles`
              : t("noResearchRuns")}
          </Text>
        </View>
        <TouchableOpacity
          onPress={onRefresh}
          style={[styles.refreshBtn, { backgroundColor: colors.card, borderColor: colors.border }]}
          activeOpacity={0.7}
        >
          <Feather name="refresh-cw" size={16} color={colors.primary} />
        </TouchableOpacity>
      </View>

      {/* Error */}
      {error && (
        <View style={[styles.errorCard, { backgroundColor: `${colors.loss}15`, borderColor: `${colors.loss}40` }]}>
          <Feather name="alert-circle" size={14} color={colors.loss} />
          <Text style={[styles.errorText, { color: colors.loss }]} numberOfLines={2}>{error}</Text>
        </View>
      )}

      {/* Loading inicial */}
      {loading && runs.length === 0 && (
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} size="large" />
        </View>
      )}

      {/* Estado vacío */}
      {!loading && !error && runs.length === 0 && (
        <View style={styles.center}>
          <Feather name="search" size={36} color={colors.mutedForeground} />
          <Text style={[styles.emptyTitle, { color: colors.foreground }]}>{t("noResearchRuns")}</Text>
          <Text style={[styles.emptyDesc, { color: colors.mutedForeground }]}>{t("noResearchDesc")}</Text>
        </View>
      )}

      {/* Lista de runs */}
      {runs.map((run) => (
        <TouchableOpacity
          key={run.run_id}
          onPress={() => onSelectRun(run)}
          activeOpacity={0.75}
          style={[styles.runCard, { backgroundColor: colors.card, borderColor: colors.border }]}
        >
          {/* Fila superior: símbolo + fecha */}
          <View style={styles.runCardTop}>
            <View style={[styles.symbolPill, { backgroundColor: `${colors.primary}20` }]}>
              <Text style={[styles.symbolPillText, { color: colors.primary }]}>{run.symbol}</Text>
            </View>
            <Text style={[styles.runDate, { color: colors.mutedForeground }]}>
              {run.generated_at ? new Date(run.generated_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" }) : run.run_id}
            </Text>
          </View>

          {/* Run ID */}
          <Text style={[styles.runId, { color: colors.mutedForeground }]}>
            ID: {run.run_id}
          </Text>

          {/* Métricas del mejor resultado */}
          {run.best_variant && (
            <View style={[styles.bestBlock, { backgroundColor: colors.secondary, borderColor: colors.border }]}>
              <View style={styles.bestRow}>
                <Text style={[styles.bestLabel, { color: colors.mutedForeground }]}>
                  {t("bestVariant")}
                </Text>
                <Text style={[styles.bestVariant, { color: colors.foreground }]}>
                  {run.best_variant.replace(/_/g, " ")}
                </Text>
              </View>
              <View style={styles.bestMetrics}>
                {run.best_pf != null && (
                  <MetricPill label="PF" value={fmt(run.best_pf)} color={pfColor(run.best_pf, colors)} colors={colors} />
                )}
                {run.best_stability != null && (
                  <MetricPill label="Stability" value={fmt(run.best_stability, 1)} color={stabilityColor(run.best_stability, colors)} colors={colors} />
                )}
                <MetricPill label={t("variantCount")} value={String(run.variant_count)} colors={colors} />
              </View>
            </View>
          )}

          <View style={styles.runCardChevron}>
            <Feather name="chevron-right" size={18} color={colors.mutedForeground} />
          </View>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// VISTA 2 — DETALLE DE RUN (tabla comparativa de variantes)
// ═════════════════════════════════════════════════════════════════════════════

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "stability_score", label: "Stability" },
  { key: "profit_factor",   label: "PF" },
  { key: "winrate",         label: "WR" },
  { key: "max_drawdown",    label: "DD" },
  { key: "total_pips",      label: "Pips" },
];

function RunDetailView({
  detail, sortedVariants, sortKey, filter, loading, colors, t, bottomPad,
  onSortChange, onFilterChange, onSelectVariant,
}: {
  detail: ExitResearchDetail;
  sortedVariants: ExitVariant[];
  sortKey: SortKey;
  filter: FilterKey;
  loading: boolean;
  colors: ReturnType<typeof useColors>;
  t: (k: string) => string;
  bottomPad: number;
  onSortChange: (k: SortKey) => void;
  onFilterChange: (k: FilterKey) => void;
  onSelectVariant: (v: ExitVariant) => void;
}) {
  // Variante de producción para resaltarla
  const prodVariant = detail.comparison.find(v =>
    v.variant === "current_production"
  );

  return (
    <ScrollView
      style={{ flex: 1 }}
      contentContainerStyle={{ paddingBottom: bottomPad + 100 }}
      showsVerticalScrollIndicator={false}
    >
      {/* ── Cabecera del run ── */}
      <View style={[styles.runDetailHeader, { borderBottomColor: colors.border }]}>
        <View style={styles.runDetailMeta}>
          <View style={[styles.symbolPill, { backgroundColor: `${colors.primary}20` }]}>
            <Text style={[styles.symbolPillText, { color: colors.primary }]}>{detail.symbol}</Text>
          </View>
          <Text style={[styles.runId, { color: colors.mutedForeground }]}>{detail.run_id}</Text>
        </View>
        <Text style={[styles.runDate, { color: colors.mutedForeground }]}>
          {new Date(detail.generated_at).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" })}
        </Text>
      </View>

      {/* ── Conclusiones (si las hay) ── */}
      {detail.conclusions?.recommended_for_live && (
        <View style={[styles.conclusionBanner, { backgroundColor: `${colors.profit}12`, borderColor: `${colors.profit}30` }]}>
          <Feather name="award" size={14} color={colors.profit} />
          <View style={{ flex: 1 }}>
            <Text style={[styles.conclusionLabel, { color: colors.mutedForeground }]}>{t("recommended")}</Text>
            <Text style={[styles.conclusionValue, { color: colors.profit }]}>
              {detail.conclusions.recommended_for_live.replace(/_/g, " ")}
            </Text>
          </View>
        </View>
      )}

      {/* ── Controles: ordenar + filtrar ── */}
      <View style={[styles.controls, { borderBottomColor: colors.border }]}>
        {/* Sort chips */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.controlsRow}>
          <Text style={[styles.controlLabel, { color: colors.mutedForeground }]}>{t("sortBy")}:</Text>
          {SORT_OPTIONS.map((opt) => (
            <Pressable
              key={opt.key}
              onPress={() => onSortChange(opt.key)}
              style={[
                styles.sortChip,
                {
                  backgroundColor: sortKey === opt.key ? colors.primary : colors.secondary,
                  borderColor: sortKey === opt.key ? colors.primary : colors.border,
                },
              ]}
            >
              <Text style={[styles.sortChipText, { color: sortKey === opt.key ? colors.primaryForeground : colors.foreground }]}>
                {opt.label}
              </Text>
            </Pressable>
          ))}

          {/* Separator */}
          <View style={[styles.controlSep, { backgroundColor: colors.border }]} />

          {/* Filter: all / positive */}
          <Pressable
            onPress={() => onFilterChange(filter === "all" ? "positive" : "all")}
            style={[
              styles.sortChip,
              { backgroundColor: filter === "positive" ? `${colors.pending}30` : colors.secondary, borderColor: filter === "positive" ? colors.pending : colors.border },
            ]}
          >
            <Feather name="filter" size={11} color={filter === "positive" ? colors.pending : colors.mutedForeground} />
            <Text style={[styles.sortChipText, { color: filter === "positive" ? colors.pending : colors.mutedForeground }]}>
              {filter === "positive" ? t("onlyPositive") : t("showAll")}
            </Text>
          </Pressable>
        </ScrollView>
      </View>

      {/* ── Tabla de variantes ── */}
      <View style={{ paddingHorizontal: 12, paddingTop: 8, gap: 8 }}>
        {loading && (
          <View style={styles.center}>
            <ActivityIndicator color={colors.primary} />
          </View>
        )}
        {sortedVariants.map((variant, idx) => (
          <VariantRow
            key={variant.variant}
            variant={variant}
            rank={idx + 1}
            isProd={variant.variant === "current_production"}
            colors={colors}
            t={t}
            onPress={() => onSelectVariant(variant)}
          />
        ))}
        {sortedVariants.length === 0 && !loading && (
          <Text style={[styles.emptyDesc, { color: colors.mutedForeground, textAlign: "center", padding: 32 }]}>
            {t("noResearchRuns")}
          </Text>
        )}
      </View>
    </ScrollView>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// COMPONENTE: VariantRow — fila de la tabla comparativa
// ═════════════════════════════════════════════════════════════════════════════

function VariantRow({
  variant, rank, isProd, colors, t, onPress,
}: {
  variant: ExitVariant;
  rank: number;
  isProd: boolean;
  colors: ReturnType<typeof useColors>;
  t: (k: string) => string;
  onPress: () => void;
}) {
  const pf       = variant.profit_factor;
  const stab     = variant.stability_score;
  const isProfit = pf >= 1.0;
  const variantColor = isProd ? colors.pending : (rank === 1 ? colors.profit : colors.foreground);

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.75}
      style={[
        styles.variantRow,
        {
          backgroundColor: colors.card,
          borderColor: isProd ? `${colors.pending}60` : (rank === 1 ? `${colors.profit}40` : colors.border),
          borderWidth: (isProd || rank === 1) ? 1.5 : 1,
        },
      ]}
    >
      {/* Rank badge */}
      <View style={[styles.rankBadge, { backgroundColor: rank === 1 ? `${colors.profit}20` : colors.secondary }]}>
        <Text style={[styles.rankText, { color: rank === 1 ? colors.profit : colors.mutedForeground }]}>
          {rank}
        </Text>
      </View>

      {/* Nombre de variante */}
      <View style={styles.variantNameCol}>
        <Text style={[styles.variantName, { color: variantColor }]} numberOfLines={1}>
          {variant.variant.replace(/_/g, " ")}
        </Text>
        {isProd && (
          <View style={[styles.prodBadge, { backgroundColor: `${colors.pending}20` }]}>
            <Text style={[styles.prodBadgeText, { color: colors.pending }]}>{t("production")}</Text>
          </View>
        )}
      </View>

      {/* Métricas compactas */}
      <View style={styles.variantMetrics}>
        {/* Stability Score */}
        <View style={styles.metricCol}>
          <Text style={[styles.metricVal, { color: stabilityColor(stab, colors) }]}>{fmt(stab, 1)}</Text>
          <Text style={[styles.metricKey, { color: colors.mutedForeground }]}>Stab</Text>
        </View>
        {/* PF */}
        <View style={styles.metricCol}>
          <Text style={[styles.metricVal, { color: pfColor(pf, colors) }]}>{fmt(pf)}</Text>
          <Text style={[styles.metricKey, { color: colors.mutedForeground }]}>PF</Text>
        </View>
        {/* WR */}
        <View style={styles.metricCol}>
          <Text style={[styles.metricVal, { color: colors.foreground }]}>{fmtPct(variant.winrate)}</Text>
          <Text style={[styles.metricKey, { color: colors.mutedForeground }]}>WR</Text>
        </View>
        {/* WF badge */}
        <View style={[styles.wfBadge, { backgroundColor: `${wfColor(variant.wf_stability, colors)}20` }]}>
          <Text style={[styles.wfText, { color: wfColor(variant.wf_stability, colors) }]}>
            {variant.wf_stability ?? "—"}
          </Text>
        </View>
      </View>

      <Feather name="chevron-right" size={14} color={colors.mutedForeground} style={{ marginLeft: 4 }} />
    </TouchableOpacity>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// VISTA 3 — DETALLE DE VARIANTE
// ═════════════════════════════════════════════════════════════════════════════

function VariantDetailView({
  variant, symbol, runId, equityCurve, loadingCurve, onLoadCurve,
  trades, tradesStats, tradesTotal, tradesHasMore, loadingTrades,
  tradesFilter, onFilterChange, onLoadMoreTrades,
  colors, t, bottomPad,
}: {
  variant:          ExitVariant;
  symbol:           string;
  runId:            string;
  equityCurve:      EquityCurveData | null;
  loadingCurve:     boolean;
  onLoadCurve:      () => void;
  trades:           ResearchTrade[];
  tradesStats:      TradePageStats | null;
  tradesTotal:      number;
  tradesHasMore:    boolean;
  loadingTrades:    boolean;
  tradesFilter:     "ALL" | "WIN" | "LOSS";
  onFilterChange:   (f: "ALL" | "WIN" | "LOSS") => void;
  onLoadMoreTrades: () => void;
  colors:           ReturnType<typeof useColors>;
  t:                (k: string) => string;
  bottomPad:        number;
}) {
  const pf   = variant.profit_factor;
  const stab = variant.stability_score;

  // Degradación PF en 4 niveles
  const degradation = [
    { label: "5k",  value: variant.pf_5k  },
    { label: "10k", value: variant.pf_10k },
    { label: "15k", value: variant.pf_15k },
    { label: "20k", value: variant.pf_20k },
  ].filter(d => d.value != null);

  // Max del eje de degradación para normalizar la barra
  const pfMax = Math.max(...degradation.map(d => d.value ?? 0), 1);

  return (
    <ScrollView
      style={{ flex: 1 }}
      contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 16, paddingBottom: bottomPad + 100, gap: 16 }}
      showsVerticalScrollIndicator={false}
    >
      {/* ── Cabecera de variante ── */}
      <View style={[styles.variantDetailHeader, { backgroundColor: colors.card, borderColor: colors.border }]}>
        <View style={styles.variantDetailTop}>
          <View style={[styles.symbolPill, { backgroundColor: `${colors.primary}20` }]}>
            <Text style={[styles.symbolPillText, { color: colors.primary }]}>{symbol}</Text>
          </View>
          {/* Stability Score grande */}
          <View style={{ alignItems: "flex-end" }}>
            <Text style={[styles.bigScore, { color: stabilityColor(stab, colors) }]}>{fmt(stab, 1)}</Text>
            <Text style={[styles.bigScoreLabel, { color: colors.mutedForeground }]}>Stability Score</Text>
          </View>
        </View>
        <Text style={[styles.variantDetailName, { color: colors.foreground }]}>
          {variant.variant.replace(/_/g, " ")}
        </Text>
      </View>

      {/* ── Equity Curve ── */}
      <SectionTitle title="Equity Curve" colors={colors} />
      <View style={[styles.curveCard, { backgroundColor: colors.card, borderColor: colors.border }]}>
        {loadingCurve && (
          <View style={[styles.center, { paddingVertical: 40 }]}>
            <ActivityIndicator color={colors.primary} />
            <Text style={[styles.emptyDesc, { color: colors.mutedForeground, marginTop: 8 }]}>
              Cargando {variant.signals ?? "?"} trades…
            </Text>
          </View>
        )}

        {!loadingCurve && equityCurve && equityCurve.points.length > 0 && (
          <>
            <EquityCurveHeader data={equityCurve} colors={colors} />
            <View style={[styles.curveDivider, { backgroundColor: colors.border }]} />
            <View style={{ paddingHorizontal: 4, paddingBottom: 8 }}>
              <InteractiveEquityChart data={equityCurve} height={200} />
            </View>
            <Text style={[styles.curveCaption, { color: colors.mutedForeground }]}>
              {equityCurve.total_trades.toLocaleString()} trades · Toca para inspeccionar · ▲ = nuevo máximo
            </Text>
          </>
        )}

        {!loadingCurve && !equityCurve && (
          <TouchableOpacity
            onPress={onLoadCurve}
            style={[styles.loadCurveBtn, { borderColor: colors.primary }]}
            activeOpacity={0.75}
          >
            <Feather name="trending-up" size={18} color={colors.primary} />
            <Text style={[styles.loadCurveBtnText, { color: colors.primary }]}>
              Ver equity curve
            </Text>
          </TouchableOpacity>
        )}

        {!loadingCurve && equityCurve && equityCurve.points.length === 0 && (
          <Text style={[styles.emptyDesc, { color: colors.mutedForeground, textAlign: "center", padding: 20 }]}>
            Sin trades disponibles para esta variante
          </Text>
        )}
      </View>

      {/* ── Grid de métricas principales ── */}
      <SectionTitle title="Métricas principales" colors={colors} />
      <View style={styles.metricsGrid}>
        <MetricCard label="Profit Factor" value={fmt(pf)} accent={pfColor(pf, colors)} colors={colors} />
        <MetricCard label="Win Rate"      value={fmtPct(variant.winrate)} accent={variant.winrate >= 50 ? colors.profit : colors.pending} colors={colors} />
        <MetricCard label="Net Pips"      value={fmtPips(variant.total_pips)} accent={variant.total_pips >= 0 ? colors.profit : colors.loss} colors={colors} />
        <MetricCard label="Max Drawdown"  value={`${fmt(variant.max_drawdown, 0)} p`} accent={colors.loss} colors={colors} />
        <MetricCard label="Sharpe"        value={fmt(variant.sharpe, 3)} colors={colors} />
        <MetricCard label="Expectancy"    value={variant.expectancy != null ? `${fmt(variant.expectancy)} p` : "—"} colors={colors} />
        <MetricCard label="Avg Win"       value={`${fmt(variant.avg_win, 1)} p`} accent={colors.profit} colors={colors} />
        <MetricCard label="Avg Loss"      value={`${fmt(variant.avg_loss, 1)} p`} accent={colors.loss} colors={colors} />
      </View>

      {/* ── MAE / MFE ── */}
      <SectionTitle title="MAE / MFE — Calidad de salida" colors={colors} />
      <View style={[styles.maeMfeBlock, { backgroundColor: colors.card, borderColor: colors.border }]}>
        {/* Profit Captured: la métrica más importante */}
        <View style={styles.capturedRow}>
          <Text style={[styles.capturedLabel, { color: colors.mutedForeground }]}>{t("profitCaptured")}</Text>
          <Text style={[styles.capturedValue, { color: variant.profit_captured_pct >= 70 ? colors.profit : colors.pending }]}>
            {fmtPct(variant.profit_captured_pct)}
          </Text>
        </View>
        {/* Barra visual de profit captured */}
        <View style={[styles.capturedBarBg, { backgroundColor: colors.secondary }]}>
          <View style={[styles.capturedBarFill, {
            width: `${Math.min(variant.profit_captured_pct, 100)}%` as any,
            backgroundColor: variant.profit_captured_pct >= 70 ? colors.profit : colors.pending,
          }]} />
        </View>

        <View style={styles.maeMfeGrid}>
          <MaeMfeCell label="MAE ganadoras" value={`${fmt(variant.mae_winners, 1)} p`} accent={colors.profit} colors={colors} desc="Retroceso medio antes de ganar" />
          <MaeMfeCell label="MAE perdedoras" value={`${fmt(variant.mae_losers, 1)} p`} accent={colors.loss} colors={colors} desc="Retroceso medio antes de perder" />
          <MaeMfeCell label="MFE ganadoras" value={`${fmt(variant.mfe_winners, 1)} p`} accent={colors.profit} colors={colors} desc="Máx. favorecimiento en ganadoras" />
          <MaeMfeCell label="MFE perdedoras" value={`${fmt(variant.mfe_losers, 1)} p`} accent={colors.loss} colors={colors} desc="Máx. favorecimiento en perdedoras" />
        </View>
      </View>

      {/* ── Walk Forward + Monte Carlo ── */}
      <SectionTitle title="Walk Forward / Monte Carlo" colors={colors} />
      <View style={[styles.wfMcBlock, { backgroundColor: colors.card, borderColor: colors.border }]}>
        {/* WF */}
        <View style={styles.wfMcRow}>
          <Text style={[styles.wfMcLabel, { color: colors.mutedForeground }]}>Walk Forward</Text>
          <View style={[styles.wfBadgeLarge, { backgroundColor: `${wfColor(variant.wf_stability, colors)}20` }]}>
            <Text style={[styles.wfTextLarge, { color: wfColor(variant.wf_stability, colors) }]}>
              {variant.wf_stability ?? "—"}
            </Text>
          </View>
        </View>
        {/* MC Ruin */}
        <View style={[styles.wfMcRow, { borderTopWidth: 1, borderTopColor: colors.border }]}>
          <Text style={[styles.wfMcLabel, { color: colors.mutedForeground }]}>MC Prob. Ruina</Text>
          <Text style={[styles.wfMcValue, {
            color: variant.mc_prob_ruin == null ? colors.mutedForeground
              : variant.mc_prob_ruin <= 0.05 ? colors.profit
              : variant.mc_prob_ruin <= 0.20 ? colors.pending
              : colors.loss,
          }]}>
            {variant.mc_prob_ruin != null ? fmtPct(variant.mc_prob_ruin * 100) : "—"}
          </Text>
        </View>
        {/* MC Profit */}
        <View style={[styles.wfMcRow, { borderTopWidth: 1, borderTopColor: colors.border }]}>
          <Text style={[styles.wfMcLabel, { color: colors.mutedForeground }]}>MC Prob. Ganancia</Text>
          <Text style={[styles.wfMcValue, { color: variant.mc_prob_profit != null && variant.mc_prob_profit >= 0.6 ? colors.profit : colors.pending }]}>
            {variant.mc_prob_profit != null ? fmtPct(variant.mc_prob_profit * 100) : "—"}
          </Text>
        </View>
      </View>

      {/* ── Degradación PF ── */}
      {degradation.length > 0 && (
        <>
          <SectionTitle title={t("pfDegradation")} colors={colors} />
          <View style={[styles.degradationBlock, { backgroundColor: colors.card, borderColor: colors.border }]}>
            {degradation.map((d, i) => {
              const w = pfMax > 0 ? ((d.value ?? 0) / pfMax) : 0;
              const color = (d.value ?? 0) >= 1.0 ? colors.profit : colors.loss;
              return (
                <View key={d.label} style={[styles.degradRow, i > 0 && { borderTopWidth: 1, borderTopColor: colors.border }]}>
                  <Text style={[styles.degradLabel, { color: colors.mutedForeground }]}>{d.label}</Text>
                  <View style={[styles.degradBarBg, { backgroundColor: colors.secondary }]}>
                    <View style={[styles.degradBarFill, { width: `${Math.min(w * 100, 100)}%` as any, backgroundColor: color }]} />
                  </View>
                  <Text style={[styles.degradValue, { color }]}>{fmt(d.value)}</Text>
                </View>
              );
            })}
          </View>
        </>
      )}

      {/* ── Trade Timeline ── */}
      <SectionTitle title="Trade Timeline" colors={colors} />

      {/* Filtros WIN / LOSS / ALL */}
      <View style={styles.tradeFilterRow}>
        {(["ALL", "WIN", "LOSS"] as const).map((f) => (
          <TouchableOpacity
            key={f}
            onPress={() => onFilterChange(f)}
            activeOpacity={0.75}
            style={[
              styles.tradeFilterChip,
              {
                backgroundColor: tradesFilter === f ? colors.primary : colors.secondary,
                borderColor: tradesFilter === f ? colors.primary : colors.border,
              },
            ]}
          >
            <Text style={[
              styles.tradeFilterText,
              { color: tradesFilter === f ? colors.primaryForeground : colors.mutedForeground },
            ]}>
              {f === "ALL"
                ? `Todos (${tradesTotal})`
                : f === "WIN"
                ? `✓ Win (${tradesStats?.wins ?? "…"})`
                : `✕ Loss (${tradesStats?.losses ?? "…"})`}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Stats resumen de trades */}
      {tradesStats && trades.length > 0 && (
        <View style={[styles.tradeStatsRow, { backgroundColor: colors.card, borderColor: colors.border }]}>
          <TradeStatCell label="MAE medio" value={`${tradesStats.avg_mae_pips.toFixed(1)} p`} colors={colors} />
          <TradeStatCell label="MFE medio" value={`${tradesStats.avg_mfe_pips.toFixed(1)} p`} colors={colors} />
          <TradeStatCell label="Duración" value={`${tradesStats.avg_duration_bars.toFixed(0)} H1`} colors={colors} />
        </View>
      )}

      {/* Lista de trades */}
      {loadingTrades && trades.length === 0 ? (
        <View style={[styles.center, { paddingVertical: 24 }]}>
          <ActivityIndicator color={colors.primary} />
        </View>
      ) : trades.length === 0 ? (
        <Text style={[styles.emptyDesc, { color: colors.mutedForeground, textAlign: "center", paddingVertical: 16 }]}>
          Sin trades disponibles
        </Text>
      ) : (
        <>
          {(() => {
            // Calcular maxMae/maxMfe del conjunto cargado para normalizar barras
            const maxMae = Math.max(...trades.map(t => t.mae_pips), 1);
            const maxMfe = Math.max(...trades.map(t => t.mfe_pips), 1);
            return trades.map(trade => (
              <ResearchTradeCard
                key={`${trade.variant}-${trade.trade_index}`}
                trade={trade}
                maxMae={maxMae}
                maxMfe={maxMfe}
              />
            ));
          })()}

          {/* Botón cargar más */}
          {tradesHasMore && (
            <TouchableOpacity
              onPress={onLoadMoreTrades}
              disabled={loadingTrades}
              activeOpacity={0.75}
              style={[styles.loadMoreBtn, { borderColor: colors.border, opacity: loadingTrades ? 0.5 : 1 }]}
            >
              {loadingTrades ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <Text style={[styles.loadMoreText, { color: colors.primary }]}>
                  Cargar más trades
                </Text>
              )}
            </TouchableOpacity>
          )}
        </>
      )}

      {/* ── Rachas y duración ── */}
      <SectionTitle title="Rachas y duración" colors={colors} />
      <View style={styles.metricsGrid}>
        <MetricCard label="Racha pérd. máx." value={variant.longest_loss_streak != null ? String(variant.longest_loss_streak) : "—"} accent={variant.longest_loss_streak != null && variant.longest_loss_streak > 50 ? colors.loss : colors.mutedForeground} colors={colors} />
        <MetricCard label="Duración media"   value={variant.avg_duration_bars != null ? `${fmt(variant.avg_duration_bars, 0)} H1` : "—"} colors={colors} />
        <MetricCard label="Trades (20k)"     value={variant.signals != null ? String(variant.signals) : "—"} colors={colors} />
        <MetricCard label="W / L"            value={variant.wins != null && variant.losses != null ? `${variant.wins} / ${variant.losses}` : "—"} colors={colors} />
      </View>
    </ScrollView>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// SUB-COMPONENTES REUTILIZABLES
// ═════════════════════════════════════════════════════════════════════════════

function SectionTitle({ title, colors }: { title: string; colors: ReturnType<typeof useColors> }) {
  return (
    <Text style={[styles.sectionTitle, { color: colors.mutedForeground }]}>
      {title.toUpperCase()}
    </Text>
  );
}

function MetricCard({ label, value, accent, colors }: {
  label: string; value: string; accent?: string; colors: ReturnType<typeof useColors>;
}) {
  return (
    <View style={[styles.metricCard, { backgroundColor: colors.card, borderColor: colors.border }]}>
      <Text style={[styles.metricCardValue, { color: accent ?? colors.foreground }]}>{value}</Text>
      <Text style={[styles.metricCardLabel, { color: colors.mutedForeground }]}>{label}</Text>
    </View>
  );
}

function MaeMfeCell({ label, value, accent, colors, desc }: {
  label: string; value: string; accent: string; colors: ReturnType<typeof useColors>; desc: string;
}) {
  return (
    <View style={[styles.maeMfeCell, { borderColor: colors.border }]}>
      <Text style={[styles.maeMfeValue, { color: accent }]}>{value}</Text>
      <Text style={[styles.maeMfeLabel, { color: colors.foreground }]}>{label}</Text>
      <Text style={[styles.maeMfeDesc, { color: colors.mutedForeground }]}>{desc}</Text>
    </View>
  );
}

function MetricPill({ label, value, color, colors }: {
  label: string; value: string; color?: string; colors: ReturnType<typeof useColors>;
}) {
  return (
    <View style={[styles.metricPill, { backgroundColor: colors.secondary, borderColor: colors.border }]}>
      <Text style={[styles.metricPillValue, { color: color ?? colors.foreground }]}>{value}</Text>
      <Text style={[styles.metricPillLabel, { color: colors.mutedForeground }]}>{label}</Text>
    </View>
  );
}

function TradeStatCell({ label, value, colors }: {
  label: string; value: string; colors: ReturnType<typeof useColors>;
}) {
  return (
    <View style={{ flex: 1, alignItems: "center", paddingVertical: 10, gap: 2 }}>
      <Text style={{ fontSize: 13, fontFamily: "Inter_700Bold", color: colors.foreground, fontVariant: ["tabular-nums"] }}>
        {value}
      </Text>
      <Text style={{ fontSize: 9, fontFamily: "Inter_500Medium", color: colors.mutedForeground, textTransform: "uppercase", letterSpacing: 0.4 }}>
        {label}
      </Text>
    </View>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// ESTILOS
// ═════════════════════════════════════════════════════════════════════════════

const styles = StyleSheet.create({
  root: { flex: 1 },

  // Back bar
  backBar: {
    flexDirection: "row", alignItems: "center", gap: 8,
    paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1,
  },
  backText: { fontSize: 14, fontFamily: "Inter_600SemiBold" },

  // Lista runs
  listHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 },
  screenTitle: { fontSize: 26, fontFamily: "Inter_700Bold" },
  screenSubtitle: { fontSize: 13, fontFamily: "Inter_400Regular", marginTop: 2 },
  refreshBtn: { width: 36, height: 36, borderRadius: 10, borderWidth: 1, alignItems: "center", justifyContent: "center" },

  errorCard: { flexDirection: "row", alignItems: "center", gap: 8, padding: 12, borderRadius: 10, borderWidth: 1 },
  errorText: { flex: 1, fontSize: 13, fontFamily: "Inter_400Regular" },

  center: { alignItems: "center", justifyContent: "center", padding: 48, gap: 12 },
  emptyTitle: { fontSize: 17, fontFamily: "Inter_600SemiBold", textAlign: "center" },
  emptyDesc: { fontSize: 13, fontFamily: "Inter_400Regular", textAlign: "center", lineHeight: 20 },

  runCard: { borderRadius: 14, borderWidth: 1, padding: 14, gap: 8 },
  runCardTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  runId: { fontSize: 11, fontFamily: "Inter_400Regular" },
  runDate: { fontSize: 12, fontFamily: "Inter_400Regular" },
  runCardChevron: { position: "absolute", right: 14, top: "50%" as any },

  bestBlock: { borderRadius: 10, borderWidth: 1, padding: 10, gap: 8 },
  bestRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  bestLabel: { fontSize: 11, fontFamily: "Inter_500Medium", textTransform: "uppercase" },
  bestVariant: { fontSize: 13, fontFamily: "Inter_600SemiBold", flex: 1 },
  bestMetrics: { flexDirection: "row", gap: 8, flexWrap: "wrap" },

  symbolPill: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  symbolPillText: { fontSize: 12, fontFamily: "Inter_700Bold", letterSpacing: 0.5 },

  metricPill: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1, alignItems: "center", minWidth: 50 },
  metricPillValue: { fontSize: 14, fontFamily: "Inter_700Bold", fontVariant: ["tabular-nums"] },
  metricPillLabel: { fontSize: 9, fontFamily: "Inter_500Medium", textTransform: "uppercase", letterSpacing: 0.4 },

  // Run detail
  runDetailHeader: { paddingHorizontal: 16, paddingVertical: 12, borderBottomWidth: 1, gap: 4 },
  runDetailMeta: { flexDirection: "row", alignItems: "center", gap: 10 },

  conclusionBanner: { flexDirection: "row", alignItems: "center", gap: 10, marginHorizontal: 12, marginTop: 10, padding: 12, borderRadius: 10, borderWidth: 1 },
  conclusionLabel: { fontSize: 10, fontFamily: "Inter_500Medium", textTransform: "uppercase", letterSpacing: 0.5 },
  conclusionValue: { fontSize: 15, fontFamily: "Inter_700Bold" },

  controls: { borderBottomWidth: 1, paddingVertical: 10 },
  controlsRow: { paddingHorizontal: 12, flexDirection: "row", alignItems: "center", gap: 8 },
  controlLabel: { fontSize: 11, fontFamily: "Inter_500Medium" },
  sortChip: { flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20, borderWidth: 1 },
  sortChipText: { fontSize: 12, fontFamily: "Inter_600SemiBold" },
  controlSep: { width: 1, height: 20 },

  // Variant row
  variantRow: { flexDirection: "row", alignItems: "center", borderRadius: 12, padding: 12, gap: 10 },
  rankBadge: { width: 28, height: 28, borderRadius: 14, alignItems: "center", justifyContent: "center" },
  rankText: { fontSize: 13, fontFamily: "Inter_700Bold" },
  variantNameCol: { flex: 1, gap: 3 },
  variantName: { fontSize: 13, fontFamily: "Inter_600SemiBold" },
  prodBadge: { alignSelf: "flex-start", paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
  prodBadgeText: { fontSize: 9, fontFamily: "Inter_700Bold", letterSpacing: 0.6 },
  variantMetrics: { flexDirection: "row", alignItems: "center", gap: 8 },
  metricCol: { alignItems: "center", minWidth: 34 },
  metricVal: { fontSize: 12, fontFamily: "Inter_700Bold", fontVariant: ["tabular-nums"] },
  metricKey: { fontSize: 9, fontFamily: "Inter_500Medium", textTransform: "uppercase" },
  wfBadge: { paddingHorizontal: 6, paddingVertical: 3, borderRadius: 5 },
  wfText: { fontSize: 9, fontFamily: "Inter_700Bold", letterSpacing: 0.4 },

  // Variant detail
  variantDetailHeader: { borderRadius: 16, borderWidth: 1, padding: 16, gap: 6 },
  variantDetailTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  variantDetailName: { fontSize: 20, fontFamily: "Inter_700Bold" },
  bigScore: { fontSize: 32, fontFamily: "Inter_700Bold", fontVariant: ["tabular-nums"] },
  bigScoreLabel: { fontSize: 11, fontFamily: "Inter_500Medium", textTransform: "uppercase", letterSpacing: 0.5, textAlign: "right" },

  sectionTitle: { fontSize: 11, fontFamily: "Inter_600SemiBold", letterSpacing: 0.8, textTransform: "uppercase", marginBottom: -4 },

  metricsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  metricCard: { flex: 1, minWidth: "44%", borderRadius: 12, borderWidth: 1, padding: 12, alignItems: "center", gap: 4 },
  metricCardValue: { fontSize: 18, fontFamily: "Inter_700Bold", fontVariant: ["tabular-nums"] },
  metricCardLabel: { fontSize: 10, fontFamily: "Inter_500Medium", textTransform: "uppercase", letterSpacing: 0.4, textAlign: "center" },

  // MAE / MFE block
  maeMfeBlock: { borderRadius: 14, borderWidth: 1, padding: 14, gap: 12 },
  capturedRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  capturedLabel: { fontSize: 12, fontFamily: "Inter_500Medium", textTransform: "uppercase", letterSpacing: 0.4 },
  capturedValue: { fontSize: 22, fontFamily: "Inter_700Bold", fontVariant: ["tabular-nums"] },
  capturedBarBg: { height: 6, borderRadius: 3, overflow: "hidden" },
  capturedBarFill: { height: 6, borderRadius: 3 },
  maeMfeGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  maeMfeCell: { flex: 1, minWidth: "44%", borderBottomWidth: 1, paddingBottom: 10, gap: 2 },
  maeMfeValue: { fontSize: 18, fontFamily: "Inter_700Bold", fontVariant: ["tabular-nums"] },
  maeMfeLabel: { fontSize: 12, fontFamily: "Inter_600SemiBold" },
  maeMfeDesc: { fontSize: 10, fontFamily: "Inter_400Regular", lineHeight: 14 },

  // WF / MC
  wfMcBlock: { borderRadius: 14, borderWidth: 1, overflow: "hidden" },
  wfMcRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 14 },
  wfMcLabel: { fontSize: 13, fontFamily: "Inter_500Medium" },
  wfMcValue: { fontSize: 16, fontFamily: "Inter_700Bold", fontVariant: ["tabular-nums"] },
  wfBadgeLarge: { paddingHorizontal: 12, paddingVertical: 5, borderRadius: 8 },
  wfTextLarge: { fontSize: 13, fontFamily: "Inter_700Bold", letterSpacing: 0.4 },

  // Degradación
  degradationBlock: { borderRadius: 14, borderWidth: 1, overflow: "hidden" },
  degradRow: { flexDirection: "row", alignItems: "center", gap: 10, padding: 12 },
  degradLabel: { fontSize: 12, fontFamily: "Inter_600SemiBold", width: 28 },
  degradBarBg: { flex: 1, height: 6, borderRadius: 3, overflow: "hidden" },
  degradBarFill: { height: 6, borderRadius: 3 },
  degradValue: { fontSize: 13, fontFamily: "Inter_700Bold", fontVariant: ["tabular-nums"], width: 44, textAlign: "right" },

  // Equity Curve block
  curveCard: { borderRadius: 14, borderWidth: 1, overflow: "hidden" },
  curveDivider: { height: 1 },
  curveCaption: {
    fontSize: 10, fontFamily: "Inter_400Regular",
    textAlign: "center", paddingBottom: 10, paddingHorizontal: 12,
  },
  loadCurveBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: 8, margin: 16, paddingVertical: 14, borderRadius: 12, borderWidth: 1.5,
  },
  loadCurveBtnText: { fontSize: 14, fontFamily: "Inter_600SemiBold" },

  // Trade Timeline
  tradeFilterRow: { flexDirection: "row", gap: 8, flexWrap: "wrap" },
  tradeFilterChip: {
    paddingHorizontal: 12, paddingVertical: 6,
    borderRadius: 20, borderWidth: 1,
  },
  tradeFilterText: { fontSize: 12, fontFamily: "Inter_600SemiBold" },
  tradeStatsRow: {
    flexDirection: "row", borderRadius: 12, borderWidth: 1,
    overflow: "hidden",
  },
  loadMoreBtn: {
    borderWidth: 1, borderRadius: 12,
    paddingVertical: 12, alignItems: "center", marginTop: 4,
  },
  loadMoreText: { fontSize: 13, fontFamily: "Inter_600SemiBold" },
});
