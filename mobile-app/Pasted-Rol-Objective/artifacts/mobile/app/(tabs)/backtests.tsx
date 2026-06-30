/**
 * Pantalla Backtests — lanzar backtests remotos con el mismo pipeline
 * que el comando /replay de Discord.
 *
 * Formulario: Par · Estrategia · Timeframe · Velas · Circuit Breaker (off / modo 1 / modo 2)
 * Resultados: Winrate, PF, Pips netos, Señales + bloque Monte Carlo
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Platform,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Feather } from "@expo/vector-icons";

import { useColors } from "@/hooks/useColors";
import { useSettings } from "@/context/SettingsContext";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import {
  BACKTEST_SYMBOLS,
  STRATEGIES_BY_SYMBOL,
  DEFAULT_STRATEGY,
  DEFAULT_BARS,
  DEFAULT_CB_LOSSES,
  DEFAULT_CB_PAUSE,
  type BacktestSymbol,
} from "@/constants/backtest";
import {
  queueBacktest,
  fetchBacktestTask,
  listBacktestTasks,
  fetchAvailableStrategies,
  type BacktestTaskDetail,
  type BacktestTaskSummary,
  type StrategyOption,
} from "@/services/backtestApi";

// ── Timeframes disponibles ────────────────────────────────────────────────────
const TIMEFRAMES = ["M5", "M15", "H1", "H4", "D1"] as const;
type Timeframe = (typeof TIMEFRAMES)[number];
const DEFAULT_TIMEFRAME: Timeframe = "H1";

// ── Timeframes permitidos por estrategia ──────────────────────────────────────
// Si la estrategia NO aparece aquí, todos los timeframes están disponibles.
// Si aparece, SOLO los timeframes listados se pueden seleccionar.
const STRATEGY_ALLOWED_TIMEFRAMES: Record<string, readonly Timeframe[]> = {
  eurusd_mtf:              ["H4"],        // D1+H4 multi-timeframe, datos H4
  btc_trend_pullback_v1:   ["H1"],        // H4+H1, resamplea H4 desde H1
  btceur_weekly_breakout:  ["H1"],        // W1 desde H1
  eurusd_asian_breakout:   ["H1"],        // Sesión asiática, necesita H1
  xauusd_psychological:    ["H1"],        // Niveles psicológicos en H1
  btceur_regime_momentum:  ["H4"],        // Requiere H4+Daily para régimen
};

function getAllowedTimeframes(strategy: string): readonly Timeframe[] {
  return STRATEGY_ALLOWED_TIMEFRAMES[strategy] ?? TIMEFRAMES;
}

function isTimeframeAllowed(strategy: string, tf: Timeframe): boolean {
  const allowed = getAllowedTimeframes(strategy);
  return allowed.includes(tf);
}

// ── Modos de Circuit Breaker ──────────────────────────────────────────────────
type CBMode = "off" | "standard" | "aggressive";

const CB_MODES: { key: CBMode; label: string; description: string }[] = [
  { key: "off", label: "Sin CB", description: "Sin circuit breaker" },
  {
    key: "standard",
    label: "Estándar",
    description: `${DEFAULT_CB_LOSSES} pérd. → ${DEFAULT_CB_PAUSE}h pausa`,
  },
  {
    key: "aggressive",
    label: "Agresivo",
    description: "3 pérd. → 72h pausa",
  },
];

function cbParams(mode: CBMode): { losses: number; pause: number } {
  switch (mode) {
    case "standard":
      return { losses: DEFAULT_CB_LOSSES, pause: DEFAULT_CB_PAUSE };
    case "aggressive":
      return { losses: 3, pause: 72 };
    default:
      return { losses: 0, pause: 0 }; // 0 = desactivado
  }
}

const STATUS_LABEL: Record<string, string> = {
  PENDING: "En cola",
  PROCESSING: "Ejecutando…",
  COMPLETED: "Completado",
  FAILED: "Error",
};

export default function BacktestsScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const { apiOverrides } = useSettings();

  // ── Formulario ──────────────────────────────────────────────────────────────
  const [symbol, setSymbol] = useState<BacktestSymbol>("EURUSD");
  const [strategy, setStrategy] = useState(DEFAULT_STRATEGY.EURUSD);
  const [timeframe, setTimeframe] = useState<Timeframe>(DEFAULT_TIMEFRAME);
  const [bars, setBars] = useState(String(DEFAULT_BARS));
  const [cbMode, setCbMode] = useState<CBMode>("standard");
  const [mcExpanded, setMcExpanded] = useState(false);

  // ── Estado de la tarea activa ───────────────────────────────────────────────
  const [running, setRunning] = useState(false);
  const [activeTask, setActiveTask] = useState<BacktestTaskDetail | null>(null);
  const [taskHistory, setTaskHistory] = useState<BacktestTaskSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const bottomPad = Platform.OS === "web" ? 34 : 0;

  // ── Cargar historial al montar ──────────────────────────────────────────────
  const loadHistory = useCallback(async () => {
    try {
      const tasks = await listBacktestTasks(apiOverrides);
      setTaskHistory(tasks);
    } catch {
      // Si el servidor no está disponible, ignoramos silenciosamente
    }
  }, [apiOverrides]);

  useEffect(() => {
    loadHistory();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loadHistory]);

  // ── Cambio de símbolo: resetear estrategia al default del par ──────────────
  const onSymbolChange = (sym: BacktestSymbol) => {
    setSymbol(sym);
    const newStrat = DEFAULT_STRATEGY[sym];
    setStrategy(newStrat);
    // Auto-corregir timeframe si no es válido para la estrategia por defecto
    if (!isTimeframeAllowed(newStrat, timeframe)) {
      setTimeframe(getAllowedTimeframes(newStrat)[0]);
    }
  };

  // ── Cambio de estrategia: auto-corregir timeframe si es necesario ──────────
  const onStrategyChange = (strat: string) => {
    setStrategy(strat);
    if (!isTimeframeAllowed(strat, timeframe)) {
      setTimeframe(getAllowedTimeframes(strat)[0]);
    }
  };

  // ── Polling de la tarea activa ──────────────────────────────────────────────
  const pollTask = useCallback(
    (taskId: number) => {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const task = await fetchBacktestTask(taskId, apiOverrides);
          setActiveTask(task);
          if (task.status === "COMPLETED" || task.status === "FAILED") {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            setRunning(false);
            loadHistory();
          }
        } catch (e) {
          setError(e instanceof Error ? e.message : String(e));
          setRunning(false);
          if (pollRef.current) clearInterval(pollRef.current);
        }
      }, 2500);
    },
    [apiOverrides, loadHistory]
  );

  // ── Lanzar backtest ─────────────────────────────────────────────────────────
  const handleRun = async () => {
    setError(null);
    setActiveTask(null);
    setRunning(true);
    const { losses, pause } = cbParams(cbMode);
    try {
      const taskId = await queueBacktest(
        {
          symbol,
          strategy,
          bars: parseInt(bars, 10) || DEFAULT_BARS,
          timeframe,
          cb_losses: losses,
          cb_pause: pause,
        },
        apiOverrides
      );
      setActiveTask({
        id: taskId,
        symbol,
        strategy,
        bars: parseInt(bars, 10),
        status: "PENDING",
        results: null,
      });
      pollTask(taskId);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setRunning(false);
    }
  };

  const mc = activeTask?.results?.monte_carlo;

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={[
        styles.content,
        { paddingBottom: bottomPad + 100 },
      ]}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
    >
      <ApiErrorBanner />

      {/* ── Formulario de configuración ── */}
      <View
        style={[
          styles.card,
          { backgroundColor: colors.card, borderColor: colors.border },
        ]}
      >
        {/* Par */}
        <Text style={[styles.fieldLabel, { color: colors.mutedForeground }]}>
          Par
        </Text>
        <View style={styles.chipRow}>
          {BACKTEST_SYMBOLS.map((sym) => (
            <Chip
              key={sym}
              label={sym}
              active={symbol === sym}
              onPress={() => onSymbolChange(sym)}
              colors={colors}
            />
          ))}
        </View>

        {/* Estrategia */}
        <Text style={[styles.fieldLabel, { color: colors.mutedForeground }]}>
          Estrategia
        </Text>
        <View style={styles.chipRow}>
          {STRATEGIES_BY_SYMBOL[symbol].map((s) => (
            <Chip
              key={s}
              label={s.replace(/_/g, " ")}
              active={strategy === s}
              onPress={() => onStrategyChange(s)}
              colors={colors}
              small
            />
          ))}
        </View>

        {/* Timeframe */}
        <Text style={[styles.fieldLabel, { color: colors.mutedForeground }]}>
          Timeframe
        </Text>
        <View style={styles.chipRow}>
          {TIMEFRAMES.map((tf) => {
            const allowed = isTimeframeAllowed(strategy, tf);
            return (
              <Chip
                key={tf}
                label={tf}
                active={timeframe === tf}
                onPress={() => setTimeframe(tf)}
                colors={colors}
                disabled={!allowed}
              />
            );
          })}
        </View>
        {STRATEGY_ALLOWED_TIMEFRAMES[strategy] ? (
          <Text style={{ fontSize: 11, fontFamily: "Inter_400Regular", color: colors.mutedForeground, marginTop: -6 }}>
            ⓘ {strategy.replace(/_/g, " ")} solo opera en {getAllowedTimeframes(strategy).join(", ")}
          </Text>
        ) : null}

        {/* Número de velas */}
        <Text style={[styles.fieldLabel, { color: colors.mutedForeground }]}>
          Número de velas
        </Text>
        <TextInput
          value={bars}
          onChangeText={setBars}
          keyboardType="numeric"
          placeholder="3000"
          placeholderTextColor={colors.mutedForeground}
          style={[
            styles.input,
            {
              color: colors.foreground,
              borderColor: colors.border,
              backgroundColor: colors.secondary,
            },
          ]}
        />

        {/* Circuit Breaker */}
        <Text style={[styles.fieldLabel, { color: colors.mutedForeground }]}>
          Circuit Breaker
        </Text>
        <View style={styles.cbRow}>
          {CB_MODES.map((mode) => (
            <TouchableOpacity
              key={mode.key}
              onPress={() => setCbMode(mode.key)}
              style={[
                styles.cbOption,
                {
                  backgroundColor:
                    cbMode === mode.key ? colors.primary : colors.secondary,
                  borderColor:
                    cbMode === mode.key ? colors.primary : colors.border,
                },
              ]}
              activeOpacity={0.75}
            >
              <Text
                style={[
                  styles.cbLabel,
                  {
                    color:
                      cbMode === mode.key
                        ? colors.primaryForeground
                        : colors.foreground,
                  },
                ]}
              >
                {mode.label}
              </Text>
              <Text
                style={[
                  styles.cbDesc,
                  {
                    color:
                      cbMode === mode.key
                        ? `${colors.primaryForeground}cc`
                        : colors.mutedForeground,
                  },
                ]}
              >
                {mode.description}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Botón de lanzar */}
        <TouchableOpacity
          onPress={handleRun}
          disabled={running}
          style={[
            styles.runBtn,
            { backgroundColor: colors.primary, opacity: running ? 0.6 : 1 },
          ]}
          activeOpacity={0.8}
        >
          {running ? (
            <ActivityIndicator color={colors.primaryForeground} />
          ) : (
            <>
              <Feather name="play" size={18} color={colors.primaryForeground} />
              <Text
                style={[styles.runText, { color: colors.primaryForeground }]}
              >
                Ejecutar backtest
              </Text>
            </>
          )}
        </TouchableOpacity>

        {error ? (
          <Text style={[styles.errorText, { color: colors.destructive }]}>
            {error}
          </Text>
        ) : null}
      </View>

      {/* ── Resultado de la tarea activa ── */}
      {activeTask ? (
        <View
          style={[
            styles.card,
            { backgroundColor: colors.card, borderColor: colors.border },
          ]}
        >
          <View style={styles.taskHeader}>
            <Text style={[styles.cardTitle, { color: colors.foreground }]}>
              {activeTask.symbol} · {activeTask.strategy.replace(/_/g, " ")}
            </Text>
            <View
              style={[
                styles.statusBadge,
                {
                  backgroundColor:
                    activeTask.status === "COMPLETED"
                      ? `${colors.profit}20`
                      : activeTask.status === "FAILED"
                      ? `${colors.loss}20`
                      : `${colors.pending}20`,
                },
              ]}
            >
              <Text
                style={[
                  styles.statusText,
                  {
                    color:
                      activeTask.status === "COMPLETED"
                        ? colors.profit
                        : activeTask.status === "FAILED"
                        ? colors.loss
                        : colors.pending,
                  },
                ]}
              >
                {STATUS_LABEL[activeTask.status] ?? activeTask.status}
              </Text>
            </View>
          </View>

          {activeTask.status === "COMPLETED" && activeTask.results ? (
            <>
              <View style={styles.metricsGrid}>
                <MetricBox
                  label="Winrate"
                  value={`${activeTask.results.winrate.toFixed(1)}%`}
                  accent={
                    (activeTask.results.winrate as number) >= 50
                      ? colors.profit
                      : colors.loss
                  }
                  colors={colors}
                />
                <MetricBox
                  label="Profit Factor"
                  value={String(activeTask.results.profit_factor)}
                  accent={
                    parseFloat(activeTask.results.profit_factor) >= 1.3
                      ? colors.profit
                      : colors.loss
                  }
                  colors={colors}
                />
                <MetricBox
                  label="Pips netos"
                  value={`${activeTask.results.total_pips >= 0 ? "+" : ""}${activeTask.results.total_pips}`}
                  accent={
                    activeTask.results.total_pips >= 0
                      ? colors.profit
                      : colors.loss
                  }
                  colors={colors}
                />
                <MetricBox
                  label="Señales"
                  value={String(activeTask.results.signals_final)}
                  colors={colors}
                />
              </View>

              {mc?.status === "success" ? (
                <View
                  style={[
                    styles.mcBlock,
                    { borderTopColor: colors.border },
                  ]}
                >
                  {/* ── Cabecera Monte Carlo ── */}
                  <TouchableOpacity
                    onPress={() => setMcExpanded((v) => !v)}
                    activeOpacity={0.7}
                    style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}
                  >
                    <Text
                      style={[styles.mcTitle, { color: colors.primary }]}
                    >
                      📊 Monte Carlo · 5.000 simulaciones
                    </Text>
                    <Feather
                      name={mcExpanded ? "chevron-up" : "chevron-down"}
                      size={18}
                      color={colors.mutedForeground}
                    />
                  </TouchableOpacity>

                  {/* ── Tarjeta de veredicto ── */}
                  {(() => {
                    const ruinPct = ((mc.prob_ruin ?? 0) as number) * 100;
                    const profitPct = ((mc.prob_profitable ?? 0) as number) * 100;
                    const isGood = ruinPct <= 5;
                    const isModerate = ruinPct > 5 && ruinPct <= 15;
                    const verdictColor = isGood
                      ? colors.profit
                      : isModerate
                      ? colors.pending
                      : colors.loss;
                    const verdictIcon = isGood ? "✅" : isModerate ? "⚠️" : "❌";
                    const verdictLabel = isGood
                      ? "Riesgo bajo"
                      : isModerate
                      ? "Riesgo moderado"
                      : "Riesgo alto";
                    const verdictDesc = isGood
                      ? "Estrategia estadísticamente estable. Buena para operar."
                      : isModerate
                      ? "Podría ser rentable, pero hay riesgo de pérdidas significativas."
                      : "Riesgo de ruina elevado. Se desaconseja operar sin ajustes.";

                    return (
                      <View
                        style={{
                          backgroundColor: `${verdictColor}15`,
                          borderRadius: 12,
                          padding: 14,
                          borderLeftWidth: 4,
                          borderLeftColor: verdictColor,
                          gap: 6,
                          marginTop: 8,
                        }}
                      >
                        <Text
                          style={{
                            fontSize: 16,
                            fontFamily: "Inter_700Bold",
                            color: verdictColor,
                          }}
                        >
                          {verdictIcon} {verdictLabel}
                        </Text>
                        <Text
                          style={{
                            fontSize: 12,
                            fontFamily: "Inter_400Regular",
                            color: colors.mutedForeground,
                            lineHeight: 18,
                          }}
                        >
                          {verdictDesc}
                        </Text>
                        <View
                          style={{
                            flexDirection: "row",
                            justifyContent: "space-around",
                            marginTop: 6,
                          }}
                        >
                          <View style={{ alignItems: "center" }}>
                            <Text
                              style={{
                                fontSize: 22,
                                fontFamily: "Inter_700Bold",
                                color: profitPct >= 60 ? colors.profit : colors.pending,
                              }}
                            >
                              {profitPct.toFixed(1)}%
                            </Text>
                            <Text
                              style={{
                                fontSize: 10,
                                fontFamily: "Inter_500Medium",
                                color: colors.mutedForeground,
                                textTransform: "uppercase",
                              }}
                            >
                              Prob. ganancia
                            </Text>
                          </View>
                          <View style={{ alignItems: "center" }}>
                            <Text
                              style={{
                                fontSize: 22,
                                fontFamily: "Inter_700Bold",
                                color: verdictColor,
                              }}
                            >
                              {ruinPct.toFixed(1)}%
                            </Text>
                            <Text
                              style={{
                                fontSize: 10,
                                fontFamily: "Inter_500Medium",
                                color: colors.mutedForeground,
                                textTransform: "uppercase",
                              }}
                            >
                              Riesgo de ruina
                            </Text>
                          </View>
                        </View>
                      </View>
                    );
                  })()}

                  {/* ── Métricas de drawdown ── */}
                  <View style={[styles.metricsGrid, { marginTop: 10 }]}>
                    <MetricBox
                      label="Drawdown esperado"
                      value={`${mc.p50_drawdown?.toFixed(0)} pip`}
                      colors={colors}
                    />
                    <MetricBox
                      label="DD peor caso (p95)"
                      value={`${mc.p95_drawdown?.toFixed(0)} pip`}
                      accent={colors.loss}
                      colors={colors}
                    />
                  </View>

                  {/* ── Equity final esperada ── */}
                  {mc.p5_equity != null && mc.p50_equity != null && mc.p95_equity != null ? (
                    <View style={[styles.metricsGrid, { marginTop: 4 }]}>
                      <MetricBox
                        label="Equity peor (p5)"
                        value={`${mc.p5_equity >= 0 ? "+" : ""}${mc.p5_equity.toFixed(0)} pip`}
                        accent={mc.p5_equity >= 0 ? colors.profit : colors.loss}
                        colors={colors}
                      />
                      <MetricBox
                        label="Equity mediana"
                        value={`${mc.p50_equity >= 0 ? "+" : ""}${mc.p50_equity.toFixed(0)} pip`}
                        accent={mc.p50_equity >= 0 ? colors.profit : colors.loss}
                        colors={colors}
                      />
                    </View>
                  ) : null}

                  {/* ── Guía expandible ── */}
                  {mcExpanded ? (
                    <View
                      style={{
                        backgroundColor: colors.secondary,
                        borderRadius: 10,
                        padding: 12,
                        gap: 10,
                        marginTop: 6,
                      }}
                    >
                      <Text
                        style={{
                          fontSize: 13,
                          fontFamily: "Inter_700Bold",
                          color: colors.foreground,
                        }}
                      >
                        ¿Cómo interpretar estos datos?
                      </Text>
                      <Text
                        style={{
                          fontSize: 12,
                          fontFamily: "Inter_400Regular",
                          color: colors.mutedForeground,
                          lineHeight: 18,
                        }}
                      >
                        La simulación Monte Carlo toma los trades del backtest y los
                        reordena aleatoriamente 5.000 veces. Esto estima cómo habría
                        cambiado el resultado si los trades hubieran llegado en un
                        orden diferente.
                      </Text>
                      <View style={{ gap: 6 }}>
                        <Text style={{ fontSize: 12, color: colors.mutedForeground, fontFamily: "Inter_400Regular", lineHeight: 18 }}>
                          <Text style={{ fontFamily: "Inter_600SemiBold", color: colors.foreground }}>Prob. ganancia:</Text>{" "}
                          Porcentaje de simulaciones que terminaron con equity positiva.
                          Un valor ≥60% indica robustez.
                        </Text>
                        <Text style={{ fontSize: 12, color: colors.mutedForeground, fontFamily: "Inter_400Regular", lineHeight: 18 }}>
                          <Text style={{ fontFamily: "Inter_600SemiBold", color: colors.foreground }}>Riesgo de ruina:</Text>{" "}
                          Porcentaje de simulaciones donde la equity cayó por debajo del
                          umbral de ruina ({mc.ruin_threshold != null ? `${mc.ruin_threshold} pip` : "−300 pip"}).
                          Ideal: ≤5%.
                        </Text>
                        <Text style={{ fontSize: 12, color: colors.mutedForeground, fontFamily: "Inter_400Regular", lineHeight: 18 }}>
                          <Text style={{ fontFamily: "Inter_600SemiBold", color: colors.foreground }}>DD esperado (p50):</Text>{" "}
                          Drawdown mediano que puedes esperar antes de recuperar. El p95 es
                          el peor escenario realista.
                        </Text>
                        <Text style={{ fontSize: 12, color: colors.mutedForeground, fontFamily: "Inter_400Regular", lineHeight: 18 }}>
                          <Text style={{ fontFamily: "Inter_600SemiBold", color: colors.foreground }}>Equity (p5/p50):</Text>{" "}
                          El p5 es el peor resultado probable, el p50 el resultado mediano.
                          Si el p5 es negativo, hay riesgo de pérdidas incluso con buena gestión.
                        </Text>
                      </View>
                    </View>
                  ) : null}
                </View>
              ) : mc?.status === "omitted" ? (
                <Text style={{ fontSize: 12, color: colors.mutedForeground, fontFamily: "Inter_400Regular", marginTop: 6 }}>
                  ⓘ Simulación Monte Carlo omitida (menos de 5 trades cerrados)
                </Text>
              ) : null}
            </>
          ) : activeTask.status === "FAILED" ? (
            <Text style={{ color: colors.destructive, fontSize: 14 }}>
              {activeTask.errorMessage ?? "Error desconocido"}
            </Text>
          ) : (
            <Text style={[styles.waitText, { color: colors.mutedForeground }]}>
              El bot procesa la cola cada ~5 s…
            </Text>
          )}
        </View>
      ) : null}

      {/* ── Historial de backtests recientes ── */}
      {taskHistory.length > 0 ? (
        <View
          style={[
            styles.card,
            { backgroundColor: colors.card, borderColor: colors.border },
          ]}
        >
          <Text style={[styles.cardTitle, { color: colors.foreground }]}>
            Historial reciente
          </Text>
          {taskHistory.slice(0, 10).map((t) => (
            <TouchableOpacity
              key={t.id}
              onPress={() => {
                setRunning(
                  t.status === "PENDING" || t.status === "PROCESSING"
                );
                fetchBacktestTask(t.id, apiOverrides)
                  .then((detail) => {
                    setActiveTask(detail);
                    if (
                      detail.status === "PENDING" ||
                      detail.status === "PROCESSING"
                    ) {
                      pollTask(t.id);
                    }
                  })
                  .catch(() => {});
              }}
              style={[
                styles.historyRow,
                { borderBottomColor: colors.border },
              ]}
              activeOpacity={0.7}
            >
              <View style={styles.historyLeft}>
                <Text
                  style={[styles.historyMain, { color: colors.foreground }]}
                >
                  {t.symbol} · {t.strategy.replace(/_/g, " ")}
                </Text>
                <Text
                  style={[
                    styles.historySub,
                    { color: colors.mutedForeground },
                  ]}
                >
                  {t.bars} velas
                </Text>
              </View>
              <View
                style={[
                  styles.historyStatus,
                  {
                    backgroundColor:
                      t.status === "COMPLETED"
                        ? `${colors.profit}20`
                        : t.status === "FAILED"
                        ? `${colors.loss}20`
                        : `${colors.pending}20`,
                  },
                ]}
              >
                <Text
                  style={[
                    styles.historyStatusText,
                    {
                      color:
                        t.status === "COMPLETED"
                          ? colors.profit
                          : t.status === "FAILED"
                          ? colors.loss
                          : colors.pending,
                    },
                  ]}
                >
                  {STATUS_LABEL[t.status] ?? t.status}
                </Text>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      ) : null}
    </ScrollView>
  );
}

// ── Sub-componentes ───────────────────────────────────────────────────────────

function Chip({
  label,
  active,
  onPress,
  colors,
  small,
  disabled,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
  colors: ReturnType<typeof useColors>;
  small?: boolean;
  disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      onPress={disabled ? undefined : onPress}
      activeOpacity={disabled ? 1 : 0.75}
      style={[
        styles.chip,
        small && styles.chipSmall,
        {
          backgroundColor: disabled
            ? `${colors.secondary}80`
            : active
            ? colors.primary
            : colors.secondary,
          borderColor: disabled
            ? `${colors.border}60`
            : active
            ? colors.primary
            : colors.border,
          opacity: disabled ? 0.4 : 1,
        },
      ]}
    >
      <Text
        style={[
          styles.chipText,
          small && styles.chipTextSmall,
          {
            color: disabled
              ? colors.mutedForeground
              : active
              ? colors.primaryForeground
              : colors.foreground,
          },
        ]}
      >
        {label}
      </Text>
    </TouchableOpacity>
  );
}

function MetricBox({
  label,
  value,
  accent,
  colors,
}: {
  label: string;
  value: string;
  accent?: string;
  colors: ReturnType<typeof useColors>;
}) {
  return (
    <View
      style={[
        styles.metricBox,
        { backgroundColor: colors.secondary, borderColor: colors.border },
      ]}
    >
      <Text
        style={[
          styles.metricValue,
          { color: accent ?? colors.foreground },
        ]}
      >
        {value}
      </Text>
      <Text style={[styles.metricLabel, { color: colors.mutedForeground }]}>
        {label}
      </Text>
    </View>
  );
}

// ── Estilos ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingHorizontal: 16, paddingTop: 8, gap: 16 },

  card: { borderRadius: 16, borderWidth: 1, padding: 16, gap: 14 },
  cardTitle: { fontSize: 16, fontFamily: "Inter_600SemiBold" },

  fieldLabel: {
    fontSize: 11,
    fontFamily: "Inter_600SemiBold",
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },

  // Chips
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
  },
  chipSmall: { paddingHorizontal: 10, paddingVertical: 6 },
  chipText: { fontSize: 13, fontFamily: "Inter_600SemiBold" },
  chipTextSmall: { fontSize: 11, fontFamily: "Inter_500Medium" },

  // Input velas
  input: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    fontFamily: "Inter_500Medium",
  },

  // Circuit Breaker
  cbRow: { flexDirection: "row", gap: 8 },
  cbOption: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 12,
    padding: 10,
    alignItems: "center",
    gap: 3,
  },
  cbLabel: { fontSize: 13, fontFamily: "Inter_700Bold" },
  cbDesc: { fontSize: 10, fontFamily: "Inter_400Regular", textAlign: "center" },

  // Botón ejecutar
  runBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 14,
    borderRadius: 12,
    marginTop: 4,
  },
  runText: { fontSize: 16, fontFamily: "Inter_700Bold" },
  errorText: { fontSize: 13, fontFamily: "Inter_500Medium" },

  // Task resultado
  taskHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  statusText: { fontSize: 12, fontFamily: "Inter_600SemiBold" },
  waitText: { fontSize: 13, fontFamily: "Inter_400Regular" },

  // Métricas grid
  metricsGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  metricBox: {
    flex: 1,
    minWidth: "44%",
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
    gap: 4,
  },
  metricValue: {
    fontSize: 20,
    fontFamily: "Inter_700Bold",
    fontVariant: ["tabular-nums"],
  },
  metricLabel: {
    fontSize: 10,
    fontFamily: "Inter_500Medium",
    textTransform: "uppercase",
    letterSpacing: 0.4,
    textAlign: "center",
  },

  // Monte Carlo
  mcBlock: { borderTopWidth: 1, paddingTop: 14, gap: 10 },
  mcTitle: { fontSize: 13, fontFamily: "Inter_700Bold" },

  // Historial
  historyRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  historyLeft: { gap: 3, flex: 1 },
  historyMain: { fontSize: 14, fontFamily: "Inter_600SemiBold" },
  historySub: { fontSize: 12, fontFamily: "Inter_400Regular" },
  historyStatus: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
  },
  historyStatusText: { fontSize: 12, fontFamily: "Inter_600SemiBold" },
});
