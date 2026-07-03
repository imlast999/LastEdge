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
