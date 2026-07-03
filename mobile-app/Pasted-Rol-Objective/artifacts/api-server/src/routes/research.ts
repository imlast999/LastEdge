/**
 * Research routes — lee artefactos generados por los scripts de Python
 * directamente del filesystem (backtest_results/).
 *
 * Endpoints:
 *   GET /api/research/exit-research
 *       Lista todos los runs de Exit Research disponibles.
 *
 *   GET /api/research/exit-research/:runId
 *       Devuelve el summary.json completo de un run específico,
 *       enriquecido con los datos de mae_mfe.csv y la tabla de degradación.
 *
 * Arquitectura de acceso:
 *   Los resultados del research son archivos estáticos en el filesystem.
 *   Este router los lee directamente sin tocar bot_state.db.
 *   Ninguna modificación al bot Python es necesaria.
 *
 * Path de resultados: RESEARCH_BASE_PATH (env BOT_RESULTS_PATH o auto-resuelto)
 */
import { Router, Request, Response } from "express";
import * as fs from "node:fs";
import * as path from "node:path";
import { logger } from "../lib/logger.js";

export const researchRouter = Router();

// ── Resolver ruta base de backtest_results ────────────────────────────────────
// Va 7 niveles arriba desde src/routes/ hasta BOT-MT5/
function resolveResultsBase(): string {
  if (process.env.BOT_RESULTS_PATH) {
    return process.env.BOT_RESULTS_PATH;
  }
  return path.resolve(
    path.dirname(new URL(import.meta.url).pathname),
    "..", "..", "..", "..", "..", "..", "..",
    "backtest_results"
  );
}

const RESULTS_BASE = resolveResultsBase();
const EXIT_RESEARCH_DIR = path.join(RESULTS_BASE, "exit_research");
const VALIDATION_DIR    = path.join(RESULTS_BASE, "validation");

// ── Helpers ───────────────────────────────────────────────────────────────────

function readJsonSafe<T>(filePath: string): T | null {
  try {
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

/** Parsea un CSV simple (primera fila = cabecera) y devuelve array de objetos. */
function parseCsv(filePath: string): Record<string, string>[] {
  try {
    const lines = fs.readFileSync(filePath, "utf-8").trim().split("\n");
    if (lines.length < 2) return [];
    const headers = lines[0].split(",").map((h) => h.trim());
    return lines.slice(1).map((line) => {
      const values = line.split(",");
      const row: Record<string, string> = {};
      headers.forEach((h, i) => { row[h] = (values[i] ?? "").trim(); });
      return row;
    });
  } catch {
    return [];
  }
}

/** Convierte un run_id de formato YYYYMMDD_HHMMSS a ISO string legible. */
function runIdToIso(runId: string): string {
  // "20260702_225143" → "2026-07-02T22:51:43Z"
  const m = runId.match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/);
  if (!m) return runId;
  return `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}Z`;
}

// ── GET /api/research/exit-research ──────────────────────────────────────────
// Lista todos los runs disponibles con sus metadatos básicos.

researchRouter.get("/exit-research", (_req: Request, res: Response) => {
  try {
    if (!fs.existsSync(EXIT_RESEARCH_DIR)) {
      res.json({ ok: true, runs: [] });
      return;
    }

    const entries = fs.readdirSync(EXIT_RESEARCH_DIR, { withFileTypes: true });
    const runs: object[] = [];

    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const runId = entry.name;
      const summaryPath = path.join(EXIT_RESEARCH_DIR, runId, "summary.json");
      if (!fs.existsSync(summaryPath)) continue;

      const summary = readJsonSafe<any>(summaryPath);
      if (!summary) continue;

      // Extraer solo los campos necesarios para el listado
      const best = summary.comparison_table?.[0] ?? null;
      runs.push({
        run_id:        summary.run_id ?? runId,
        generated_at:  summary.generated_at ?? runIdToIso(runId),
        symbol:        summary.symbol ?? "UNKNOWN",
        validation_mode: summary.validation_mode ?? null,
        variant_count: summary.comparison_table?.length ?? 0,
        best_variant:  best?.variant ?? null,
        best_pf:       best?.profit_factor ?? null,
        best_stability: best?.stability_score ?? null,
      });
    }

    // Más reciente primero
    runs.sort((a: any, b: any) =>
      (b.run_id ?? "").localeCompare(a.run_id ?? "")
    );

    res.json({ ok: true, runs });
  } catch (err) {
    logger.error({ err }, "GET /api/research/exit-research error");
    res.status(500).json({ ok: false, message: "Failed to list exit research runs" });
  }
});

// ── GET /api/research/exit-research/:runId ────────────────────────────────────
// Detalle completo de un run: comparison_table, degradation_table,
// mae_mfe por variante, y métricas completas del nivel máximo (20k).

researchRouter.get("/exit-research/:runId", (req: Request, res: Response) => {
  const { runId } = req.params as { runId: string };

  // Validación básica del runId para evitar path traversal
  if (!runId || !/^[\w-]+$/.test(runId)) {
    res.status(400).json({ ok: false, message: "Invalid run ID" });
    return;
  }

  const runDir = path.join(EXIT_RESEARCH_DIR, runId);
  if (!fs.existsSync(runDir)) {
    res.status(404).json({ ok: false, message: "Run not found" });
    return;
  }

  try {
    // 1. summary.json — fuente principal
    const summary = readJsonSafe<any>(path.join(runDir, "summary.json"));
    if (!summary) {
      res.status(404).json({ ok: false, message: "summary.json not found or invalid" });
      return;
    }

    // 2. mae_mfe.csv — enriquece cada variante con datos MAE/MFE detallados
    const maeMfeRows = parseCsv(path.join(runDir, "mae_mfe.csv"));
    const maeMfeByVariant: Record<string, Record<string, string>> = {};
    for (const row of maeMfeRows) {
      if (row.variant) maeMfeByVariant[row.variant] = row;
    }

    // 3. Construir tabla comparativa enriquecida
    // Para cada variante del comparison_table, añadimos:
    //   - mae_winners, mae_losers, mfe_winners, mfe_losers del mae_mfe.csv
    //   - métricas completas del nivel 20k (desde results[variant]["20000"])
    //   - tabla de degradación (desde degradation_table)
    const maxLevel = "20000";
    const comparison = (summary.comparison_table ?? []).map((row: any) => {
      const variantId = row.variant;
      const maeMfe    = maeMfeByVariant[variantId] ?? {};
      const fullMetrics = summary.results?.[variantId]?.[maxLevel]?.metrics ?? null;
      const degradation = summary.degradation_table?.[variantId] ?? null;

      return {
        // Ranking básico
        rank:             row.rank,
        variant:          variantId,
        profit_factor:    row.profit_factor,
        winrate:          row.winrate,
        total_pips:       row.total_pips,
        max_drawdown:     row.max_drawdown,
        sharpe:           row.sharpe,
        stability_score:  row.stability_score,
        sortino:          row.sortino,
        calmar:           row.calmar,
        recovery_factor:  row.recovery_factor,
        mc_prob_ruin:     row.mc_prob_ruin,
        mc_prob_profit:   row.mc_prob_profit,
        wf_stability:     fullMetrics?.wf_stability ?? null,
        // MAE / MFE — priorizar mae_mfe.csv, caer a fullMetrics si no existe
        mae_mean:         parseFloat(maeMfe.mae_mean  ?? "0") || (fullMetrics?.mae_mean  ?? 0),
        mfe_mean:         parseFloat(maeMfe.mfe_mean  ?? "0") || (fullMetrics?.mfe_mean  ?? 0),
        mae_winners:      parseFloat(maeMfe.mae_winners ?? "0") || (fullMetrics?.mae_winners ?? 0),
        mae_losers:       parseFloat(maeMfe.mae_losers  ?? "0") || (fullMetrics?.mae_losers  ?? 0),
        mfe_winners:      parseFloat(maeMfe.mfe_winners ?? "0") || (fullMetrics?.mfe_winners ?? 0),
        mfe_losers:       parseFloat(maeMfe.mfe_losers  ?? "0") || (fullMetrics?.mfe_losers  ?? 0),
        profit_captured_pct: parseFloat(maeMfe.profit_captured_pct ?? "0") || (fullMetrics?.profit_captured_pct ?? 0),
        avg_win:          parseFloat(maeMfe.avg_win  ?? "0") || (fullMetrics?.avg_win  ?? 0),
        avg_loss:         parseFloat(maeMfe.avg_loss ?? "0") || (fullMetrics?.avg_loss ?? 0),
        // Métricas adicionales del nivel 20k
        signals:          fullMetrics?.signals ?? null,
        wins:             fullMetrics?.wins ?? null,
        losses:           fullMetrics?.losses ?? null,
        expectancy:       fullMetrics?.expectancy ?? null,
        longest_loss_streak: fullMetrics?.longest_loss_streak ?? null,
        avg_duration_bars:   fullMetrics?.avg_duration_bars ?? null,
        // Degradación PF entre niveles
        pf_5k:    degradation?.["5000"]  ?? null,
        pf_10k:   degradation?.["10000"] ?? null,
        pf_15k:   degradation?.["15000"] ?? null,
        pf_20k:   degradation?.["20000"] ?? null,
      };
    });

    res.json({
      ok: true,
      run_id:          summary.run_id,
      generated_at:    summary.generated_at,
      symbol:          summary.symbol,
      validation_mode: summary.validation_mode,
      conclusions:     summary.conclusions ?? null,
      comparison,
    });
  } catch (err) {
    logger.error({ err, runId }, "GET /api/research/exit-research/:runId error");
    res.status(500).json({ ok: false, message: "Failed to read exit research run" });
  }
});
