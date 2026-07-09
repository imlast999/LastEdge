/**
 * researchApi.ts — Cliente tipado para los endpoints de investigación cuantitativa.
 *
 * Consume:
 *   GET /api/research/exit-research          → lista de runs
 *   GET /api/research/exit-research/:runId   → detalle completo de un run
 */
import { resolveApiConfig } from "@/lib/apiConfig";

// ── Tipos ────────────────────────────────────────────────────────────────────

export interface ExitResearchRun {
  run_id:          string;
  generated_at:    string;
  symbol:          string;
  validation_mode: string | null;
  variant_count:   number;
  best_variant:    string | null;
  best_pf:         number | null;
  best_stability:  number | null;
}

/** Variante enriquecida con todos los datos del nivel 20k. */
export interface ExitVariant {
  // Identidad
  rank:             number;
  variant:          string;
  // P&L
  profit_factor:    number;
  winrate:          number;
  total_pips:       number;
  avg_win:          number;
  avg_loss:         number;
  expectancy:       number | null;
  // Riesgo
  max_drawdown:     number;
  sharpe:           number;
  sortino:          number | null;
  calmar:           number | null;
  recovery_factor:  number | null;
  stability_score:  number;
  // Rachas / duración
  signals:          number | null;
  wins:             number | null;
  losses:           number | null;
  longest_loss_streak: number | null;
  avg_duration_bars:   number | null;
  // MAE / MFE
  mae_mean:         number;
  mfe_mean:         number;
  mae_winners:      number;
  mae_losers:       number;
  mfe_winners:      number;
  mfe_losers:       number;
  profit_captured_pct: number;
  // Walk-Forward / Monte Carlo
  wf_stability:     string | null;
  mc_prob_ruin:     number | null;
  mc_prob_profit:   number | null;
  // Degradación PF por nivel
  pf_5k:  number | null;
  pf_10k: number | null;
  pf_15k: number | null;
  pf_20k: number | null;
}

export interface ExitResearchConclusions {
  highest_profit:         string | null;
  lowest_drawdown:        string | null;
  most_robust:            string | null;
  best_walk_forward:      string | null;
  lowest_ruin_probability: string | null;
  recommended_for_live:   string | null;
}

export interface ExitResearchDetail {
  run_id:          string;
  generated_at:    string;
  symbol:          string;
  validation_mode: string | null;
  conclusions:     ExitResearchConclusions | null;
  comparison:      ExitVariant[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function authHeaders(token: string): Record<string, string> {
  if (!token) return {};
  return { Authorization: `Bearer ${token}`, "X-Api-Key": token };
}

async function apiFetch<T>(
  path: string,
  overrides?: { url?: string; token?: string }
): Promise<T> {
  const { url, token } = resolveApiConfig(overrides);
  const res = await fetch(`${url}${path}`, { headers: authHeaders(token) });
  const data = await res.json();
  if (!res.ok || data.ok === false) {
    throw new Error((data as any).message ?? `HTTP ${res.status}`);
  }
  return data as T;
}

// ── API pública ───────────────────────────────────────────────────────────────

/** Devuelve la lista de todos los runs de Exit Research disponibles. */
export async function listExitResearchRuns(
  overrides?: { url?: string; token?: string }
): Promise<ExitResearchRun[]> {
  const data = await apiFetch<{ ok: boolean; runs: ExitResearchRun[] }>(
    "/api/research/exit-research",
    overrides
  );
  return data.runs;
}

/** Devuelve el detalle completo (todas las variantes + métricas) de un run. */
export async function fetchExitResearchDetail(
  runId: string,
  overrides?: { url?: string; token?: string }
): Promise<ExitResearchDetail> {
  return apiFetch<ExitResearchDetail>(
    `/api/research/exit-research/${encodeURIComponent(runId)}`,
    overrides
  );
}

// ── Equity Curve ──────────────────────────────────────────────────────────────

/** Un punto de la equity curve acumulada. */
export interface EquityCurvePoint {
  trade_index:   number;  // número ordinal del trade (eje X)
  bar_index:     number;  // índice de vela en el dataset
  exit_bar:      number;
  result:        "WIN" | "LOSS";
  profit_pips:   number;  // P&L del trade individual
  equity:        number;  // equity acumulada hasta este punto
  drawdown:      number;  // drawdown en pips desde el último pico
  mae_pips:      number;
  mfe_pips:      number;
  duration_bars: number;
  is_new_high:   boolean;
}

export interface EquityCurveData {
  variant:       string;
  total_trades:  number;
  final_equity:  number;
  max_drawdown:  number;
  new_highs:     number;
  wins:          number;
  losses:        number;
  points:        EquityCurvePoint[];
}

/**
 * Carga la equity curve de una variante.
 * step > 1 para decimación (reduce el payload para variantes con muchos trades).
 */
export async function fetchEquityCurve(
  runId: string,
  variant: string,
  step = 1,
  overrides?: { url?: string; token?: string }
): Promise<EquityCurveData> {
  const params = new URLSearchParams({ variant });
  if (step > 1) params.set("step", String(step));
  return apiFetch<EquityCurveData>(
    `/api/research/exit-research/${encodeURIComponent(runId)}/equity?${params}`,
    overrides
  );
}

// ── Trade Timeline ────────────────────────────────────────────────────────────

/** Un trade individual enriquecido con equity acumulada hasta ese punto. */
export interface ResearchTrade {
  trade_index:   number;
  variant:       string;
  result:        "WIN" | "LOSS";
  profit_pips:   number;
  equity:        number;   // equity acumulada en ese punto
  drawdown:      number;   // drawdown en pips desde el pico anterior
  mae_pips:      number;
  mfe_pips:      number;
  duration_bars: number;
  bar_index:     number;
  exit_bar:      number;
  is_new_high:   boolean;
  timestamp?:    string;
}

export interface TradePageStats {
  wins:              number;
  losses:            number;
  avg_mae_pips:      number;
  avg_mfe_pips:      number;
  avg_duration_bars: number;
}

export interface TradesPage {
  variant:  string;
  total:    number;
  page:     number;
  limit:    number;
  has_more: boolean;
  stats:    TradePageStats;
  trades:   ResearchTrade[];
}

/** Carga una página de trades de una variante.
 * result: "WIN" | "LOSS" | undefined (todos)
 */
export async function fetchVariantTrades(
  runId: string,
  variant: string,
  options?: {
    page?:   number;
    limit?:  number;
    result?: "WIN" | "LOSS";
    overrides?: { url?: string; token?: string };
  }
): Promise<TradesPage> {
  const { page = 0, limit = 50, result, overrides } = options ?? {};
  const params = new URLSearchParams({ variant, page: String(page), limit: String(limit) });
  if (result) params.set("result", result);
  return apiFetch<TradesPage>(
    `/api/research/exit-research/${encodeURIComponent(runId)}/trades?${params}`,
    overrides
  );
}

// ── Monte Carlo Fan Chart ──────────────────────────────────────────────────────

export interface MonteCarloFanData {
  variant:  string;
  p5:       number[];
  p25:      number[];
  p50:      number[];
  p75:      number[];
  p95:      number[];
  original: number[];
}

/** Carga los datos de percentiles de Monte Carlo para una variante. */
export async function fetchMonteCarloFan(
  runId: string,
  variant: string,
  overrides?: { url?: string; token?: string }
): Promise<MonteCarloFanData> {
  const params = new URLSearchParams({ variant });
  return apiFetch<MonteCarloFanData>(
    `/api/research/exit-research/${encodeURIComponent(runId)}/montecarlo?${params}`,
    overrides
  );
}
