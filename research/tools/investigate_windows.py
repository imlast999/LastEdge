#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
investigate_windows.py — Investigación profunda de ventanas walk-forward

Descarga los datos reales de MT5, reconstruye cada ventana del walk-forward
y calcula métricas de régimen de mercado (ATR, ADX, pendiente EMA, estructura)
para cada una. Compara ventanas problemáticas vs ganadoras trade por trade.

Uso:
    python research/tools/investigate_windows.py
    python research/tools/investigate_windows.py --windows 8,9           # solo esas
    python research/tools/investigate_windows.py --all                   # todas
    python research/tools/investigate_windows.py --save                  # guarda JSON
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# UTF-8 en Windows
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import logging
logging.basicConfig(level=logging.WARNING)
for noisy in ['core.engine','core.scoring','strategies.eurusd','signals','mt5_client']:
    logging.getLogger(noisy).setLevel(logging.ERROR)

import numpy as np
import pandas as pd

# ── Configuración del walk-forward original ──────────────────────────────────
WF_CONFIG = {
    "symbol":    "EURUSD",
    "strategy":  "eurusd_simple",
    "total_bars": 20000,
    "lookback":   210,
    "train_bars": 4320,
    "test_bars":  720,
    "step_bars":  720,
    "cb_losses":  3,
    "cb_pause":   72,
    "timeframe":  "H1",
    "params": {"sl_atr_multiplier": 1.5, "tp_atr_multiplier": 6.0},
}

# Ventanas del walk-forward (índices en el df completo, sin lookback)
# Reproducidos desde el log: train [start:end] test [start:end]
WF_WINDOWS = [
    {"w":  1, "train_start":  720, "train_end": 5040, "test_start": 5040,  "test_end": 5760},
    {"w":  2, "train_start": 1440, "train_end": 5760, "test_start": 5760,  "test_end": 6480},
    {"w":  3, "train_start": 2160, "train_end": 6480, "test_start": 6480,  "test_end": 7200},
    {"w":  4, "train_start": 2880, "train_end": 7200, "test_start": 7200,  "test_end": 7920},
    {"w":  5, "train_start": 3600, "train_end": 7920, "test_start": 7920,  "test_end": 8640},
    {"w":  6, "train_start": 4320, "train_end": 8640, "test_start": 8640,  "test_end": 9360},
    {"w":  7, "train_start": 5040, "train_end": 9360, "test_start": 9360,  "test_end":10080},
    {"w":  8, "train_start": 5760, "train_end":10080, "test_start":10080,  "test_end":10800},
    {"w":  9, "train_start": 6480, "train_end":10800, "test_start":10800,  "test_end":11520},
    {"w": 10, "train_start": 7200, "train_end":11520, "test_start":11520,  "test_end":12240},
    {"w": 11, "train_start": 7920, "train_end":12240, "test_start":12240,  "test_end":12960},
    {"w": 12, "train_start": 8640, "train_end":12960, "test_start":12960,  "test_end":13680},
    {"w": 13, "train_start": 9360, "train_end":13680, "test_start":13680,  "test_end":14400},
    {"w": 14, "train_start":10080, "train_end":14400, "test_start":14400,  "test_end":15120},
    {"w": 15, "train_start":10800, "train_end":15120, "test_start":15120,  "test_end":15840},
    {"w": 16, "train_start":11520, "train_end":15840, "test_start":15840,  "test_end":16560},
    {"w": 17, "train_start":12240, "train_end":16560, "test_start":16560,  "test_end":17280},
    {"w": 18, "train_start":12960, "train_end":17280, "test_start":17280,  "test_end":18000},
    {"w": 19, "train_start":13680, "train_end":18000, "test_start":18000,  "test_end":18720},
    {"w": 20, "train_start":14400, "train_end":18720, "test_start":18720,  "test_end":19440},
]

# Resultados conocidos del walk-forward
WF_RESULTS = {
    1:  {"pf_train":1.20,"pf_test":0.71,"wr_train":40.4,"wr_test":33.3,"test_signals":30,"test_pips":-166.0},
    2:  {"pf_train":1.24,"pf_test":1.30,"wr_train":41.9,"wr_test":47.1,"test_signals":35,"test_pips": 110.7},
    3:  {"pf_train":1.24,"pf_test":0.92,"wr_train":43.1,"wr_test":36.0,"test_signals":25,"test_pips": -30.2},
    4:  {"pf_train":1.25,"pf_test":0.80,"wr_train":43.1,"wr_test":30.3,"test_signals":33,"test_pips": -93.1},
    5:  {"pf_train":1.00,"pf_test":1.28,"wr_train":37.7,"wr_test":44.8,"test_signals":29,"test_pips":  87.0},
    6:  {"pf_train":1.17,"pf_test":1.21,"wr_train":41.2,"wr_test":42.9,"test_signals":28,"test_pips":  75.0},
    7:  {"pf_train":0.99,"pf_test":2.29,"wr_train":38.8,"wr_test":60.0,"test_signals":15,"test_pips": 280.0},
    8:  {"pf_train":1.20,"pf_test":0.61,"wr_train":42.6,"wr_test":30.4,"test_signals":23,"test_pips":-180.0},
    9:  {"pf_train":1.16,"pf_test":0.50,"wr_train":41.8,"wr_test":24.1,"test_signals":29,"test_pips":-230.0},
    10: {"pf_train":1.04,"pf_test":0.67,"wr_train":39.9,"wr_test":20.0,"test_signals":25,"test_pips":-130.0},
    11: {"pf_train":0.99,"pf_test":0.90,"wr_train":38.6,"wr_test":30.8,"test_signals":26,"test_pips": -55.0},
    12: {"pf_train":0.99,"pf_test":0.98,"wr_train":37.5,"wr_test":33.3,"test_signals":21,"test_pips":  -8.0},
    13: {"pf_train":1.01,"pf_test":0.84,"wr_train":37.3,"wr_test":31.0,"test_signals":29,"test_pips": -70.0},
    14: {"pf_train":0.80,"pf_test":0.73,"wr_train":29.2,"wr_test":30.8,"test_signals":26,"test_pips": -90.0},
    15: {"pf_train":0.86,"pf_test":0.86,"wr_train":30.4,"wr_test":34.5,"test_signals":29,"test_pips": -40.0},
    16: {"pf_train":0.88,"pf_test":1.22,"wr_train":31.4,"wr_test":40.7,"test_signals":27,"test_pips":  95.0},
    17: {"pf_train":0.95,"pf_test":1.16,"wr_train":34.8,"wr_test":38.7,"test_signals":31,"test_pips": 120.0},
    18: {"pf_train":1.01,"pf_test":2.55,"wr_train":36.7,"wr_test":59.4,"test_signals":32,"test_pips": 480.0},
    19: {"pf_train":1.19,"pf_test":0.82,"wr_train":41.7,"wr_test":36.7,"test_signals":30,"test_pips": -80.0},
    20: {"pf_train":1.12,"pf_test":1.42,"wr_train":41.7,"wr_test":52.0,"test_signals":25,"test_pips": 175.0},
}

# ── Helpers de indicadores ────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df['high'], df['low'], df['close']
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index."""
    h, l, c = df['high'], df['low'], df['close']
    prev_h = h.shift(1)
    prev_l = l.shift(1)
    prev_c = c.shift(1)

    up_move   = h - prev_h
    down_move = prev_l - l

    plus_dm  = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)

    atr_s     = pd.Series(tr).ewm(span=period, adjust=False).mean()
    plus_di   = 100 * pd.Series(plus_dm).ewm(span=period, adjust=False).mean() / atr_s
    minus_di  = 100 * pd.Series(minus_dm).ewm(span=period, adjust=False).mean() / atr_s

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx_s = dx.ewm(span=period, adjust=False).mean()
    return adx_s

def classify_regime(atr_rel: float, adx_mean: float, ema50_slope: float,
                    ema200_slope: float, pct_above_ema200: float) -> str:
    """
    Clasifica el régimen de mercado de una ventana.
    Reglas (en orden de precedencia):
      1. HIGH_VOLATILITY : ATR relativo > 0.8% del precio
      2. STRONG_TREND    : ADX > 25 Y pendiente EMA50 clara (|slope| > 0.0002/barra)
      3. WEAK_TREND      : ADX 18-25 O pendiente EMA50 moderada
      4. SIDEWAYS        : ADX < 18 Y pendiente EMA50 plana
      5. LOW_VOLATILITY  : ATR relativo < 0.35% del precio
    """
    if atr_rel > 0.008:
        return "HIGH_VOLATILITY"
    if atr_rel < 0.0035:
        return "LOW_VOLATILITY"
    if adx_mean > 25 and abs(ema50_slope) > 0.0002:
        return "STRONG_TREND"
    if adx_mean < 18 and abs(ema50_slope) < 0.0001:
        return "SIDEWAYS"
    return "WEAK_TREND"


def analyze_window_regime(df_test: pd.DataFrame) -> dict:
    """Calcula métricas de régimen para una ventana de datos."""
    df = df_test.copy().reset_index(drop=True)

    # EMAs
    e20  = ema(df['close'], 20)
    e50  = ema(df['close'], 50)
    e200 = ema(df['close'], 200)

    # Pendientes (diferencia media entre velas)
    ema50_slope  = (e50.iloc[-1]  - e50.iloc[0])  / max(len(df)-1, 1)
    ema200_slope = (e200.iloc[-1] - e200.iloc[0]) / max(len(df)-1, 1)

    # Distancia EMA50-EMA200 (% relativo)
    ema_distance_pct = abs(e50.mean() - e200.mean()) / e200.mean()

    # % velas por encima de EMA200
    pct_above_ema200 = (df['close'] > e200).mean()

    # ATR
    atr_s    = atr(df)
    atr_mean = atr_s.mean()
    atr_rel  = atr_mean / df['close'].mean()   # relativo al precio

    # ADX
    adx_s    = adx(df)
    adx_mean = adx_s.mean()
    adx_max  = adx_s.max()
    adx_min  = adx_s.min()

    # Rango diario y semanal promedio (H1: 24 velas/día, 120/semana)
    n = len(df)
    daily_ranges  = []
    weekly_ranges = []
    for start in range(0, n - 24, 24):
        chunk = df.iloc[start:start+24]
        daily_ranges.append(chunk['high'].max() - chunk['low'].min())
    for start in range(0, n - 120, 120):
        chunk = df.iloc[start:start+120]
        weekly_ranges.append(chunk['high'].max() - chunk['low'].min())

    avg_daily_range  = np.mean(daily_ranges)  if daily_ranges  else 0.0
    avg_weekly_range = np.mean(weekly_ranges) if weekly_ranges else 0.0

    regime = classify_regime(atr_rel, adx_mean, ema50_slope, ema200_slope, pct_above_ema200)

    return {
        "ema50_slope":       round(float(ema50_slope),  6),
        "ema200_slope":      round(float(ema200_slope), 6),
        "ema_distance_pct":  round(float(ema_distance_pct) * 100, 4),  # en %
        "pct_above_ema200":  round(float(pct_above_ema200) * 100, 1),
        "atr_mean":          round(float(atr_mean),  5),
        "atr_rel_pct":       round(float(atr_rel) * 100, 4),
        "atr_max":           round(float(atr_s.max()), 5),
        "atr_min":           round(float(atr_s.min()), 5),
        "adx_mean":          round(float(adx_mean), 2),
        "adx_max":           round(float(adx_max),  2),
        "adx_min":           round(float(adx_min),  2),
        "avg_daily_range":   round(float(avg_daily_range), 5),
        "avg_weekly_range":  round(float(avg_weekly_range), 5),
        "regime":            regime,
    }


def run_window_signals(df_full: pd.DataFrame, window: dict) -> list:
    """Re-ejecuta el replay sobre la ventana test y devuelve las señales."""
    from core.replay_engine import ReplayEngine
    from core.engine import get_trading_engine

    lookback  = WF_CONFIG["lookback"]
    test_start = window["test_start"]
    test_end   = window["test_end"]

    # El slice incluye el lookback anterior
    df_slice = df_full.iloc[test_start - lookback : test_end].copy()

    get_trading_engine().reset_replay_state(WF_CONFIG["symbol"])
    engine = ReplayEngine(
        lookback_window=lookback,
        max_forward_bars=120,
        cb_consecutive_losses=WF_CONFIG["cb_losses"],
        cb_pause_bars=WF_CONFIG["cb_pause"],
    )
    engine.run_replay(
        symbol=WF_CONFIG["symbol"],
        bars=WF_CONFIG["test_bars"],
        strategy=WF_CONFIG["strategy"],
        config=WF_CONFIG["params"],
        skip_duplicate_filter=True,
        df_override=df_slice,
        timeframe=WF_CONFIG["timeframe"],
    )
    return engine.get_signals()


def analyze_signals(signals: list) -> dict:
    """Analiza las señales de una ventana (duración, RR efectivo, distribución de pérdidas)."""
    if not signals:
        return {"count": 0}

    closed = [s for s in signals if s.result in ("WIN", "LOSS")]
    wins   = [s for s in closed if s.result == "WIN"]
    losses = [s for s in closed if s.result == "LOSS"]

    durations = []
    for s in closed:
        if s.exit_bar and s.bar_index:
            durations.append(s.exit_bar - s.bar_index)

    win_pips  = [s.profit_pips for s in wins  if s.profit_pips is not None]
    loss_pips = [s.profit_pips for s in losses if s.profit_pips is not None]

    # RR efectivo: ganancia media / |pérdida media|
    avg_win  = np.mean(win_pips)  if win_pips  else 0.0
    avg_loss = abs(np.mean(loss_pips)) if loss_pips else 0.0
    eff_rr   = avg_win / avg_loss if avg_loss > 0 else 0.0

    # Distribución de pérdidas: muchas pequeñas o pocas grandes
    if loss_pips:
        loss_arr  = np.array([abs(p) for p in loss_pips])
        loss_std  = float(np.std(loss_arr))
        loss_mean = float(np.mean(loss_arr))
        loss_max  = float(np.max(loss_arr))
        # Si la pérdida máxima es >3x la media → pocas pérdidas grandes
        few_large = loss_max > 3 * loss_mean
    else:
        loss_std = loss_mean = loss_max = 0.0
        few_large = False

    return {
        "count":         len(signals),
        "closed":        len(closed),
        "wins":          len(wins),
        "losses":        len(losses),
        "winrate":       round(len(wins)/len(closed)*100, 1) if closed else 0.0,
        "avg_win_pips":  round(avg_win,  1),
        "avg_loss_pips": round(-avg_loss, 1),
        "eff_rr":        round(eff_rr, 2),
        "dur_avg":       round(np.mean(durations), 1) if durations else 0.0,
        "dur_max":       max(durations) if durations else 0,
        "dur_min":       min(durations) if durations else 0,
        "loss_std":      round(loss_std, 1),
        "loss_max_pips": round(loss_max, 1),
        "few_large_losses": few_large,
        "pf_computed":   round(sum(win_pips)/abs(sum(loss_pips)), 3)
                         if loss_pips and sum(loss_pips) != 0 else 0.0,
    }


# ── Impresión ─────────────────────────────────────────────────────────────────

BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
CYAN   = "\033[36m"
GRAY   = "\033[90m"
RESET  = "\033[0m"

REGIME_COLOR = {
    "STRONG_TREND":    GREEN,
    "WEAK_TREND":      YELLOW,
    "SIDEWAYS":        RED,
    "HIGH_VOLATILITY": CYAN,
    "LOW_VOLATILITY":  GRAY,
}

def pf_color(pf):
    if pf >= 1.2: return GREEN
    if pf >= 1.0: return YELLOW
    return RED

def print_header(title):
    print(f"\n{BOLD}{'═'*72}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BOLD}{'═'*72}{RESET}")

def print_section(title):
    print(f"\n{CYAN}{'─'*72}{RESET}")
    print(f"{CYAN}  {title}{RESET}")
    print(f"{CYAN}{'─'*72}{RESET}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", type=str, default="",
                        help="Ventanas a analizar en detalle, ej: 8,9 (default: 8,9 + top2/bottom2)")
    parser.add_argument("--all",  action="store_true", help="Analizar régimen de todas las ventanas")
    parser.add_argument("--save", action="store_true", help="Guardar resultado en research/run_cards/")
    args = parser.parse_args()

    focus_windows = [int(x) for x in args.windows.split(",") if x.strip()] if args.windows else [8, 9]
    # Siempre añadir las top2/bottom2 para comparación
    by_pf = sorted(WF_RESULTS.items(), key=lambda x: x[1]["pf_test"])
    bottom2 = [w for w, _ in by_pf[:2]]
    top2    = [w for w, _ in by_pf[-2:]]
    compare_windows = sorted(set(focus_windows + bottom2 + top2))

    analyze_all = args.all
    windows_to_run = list(range(1, 21)) if analyze_all else compare_windows

    # ── 1. Conectar MT5 y descargar datos ─────────────────────────────────────
    print_header("INVESTIGACIÓN DE VENTANAS WALK-FORWARD — eurusd_simple")
    print(f"\n  Conectando a MT5...")
    try:
        from dotenv import load_dotenv
        import MetaTrader5 as mt5
        from mt5_client import get_candles, initialize as mt5_init
        load_dotenv()
        mt5_init()
        info = mt5.account_info()
        if info:
            print(f"  {GREEN}✓ MT5: cuenta {info.login} | {info.server}{RESET}")
    except Exception as e:
        print(f"  {RED}✗ Error conectando MT5: {e}{RESET}")
        sys.exit(1)

    total_needed = WF_CONFIG["total_bars"] + WF_CONFIG["lookback"]
    print(f"  Descargando {total_needed} velas EURUSD H1...")
    tf_map = {"H1": mt5.TIMEFRAME_H1}
    df_full = get_candles("EURUSD", tf_map["H1"], total_needed)
    if df_full is None or len(df_full) < total_needed:
        print(f"  {RED}✗ Datos insuficientes{RESET}")
        sys.exit(1)
    df_full = df_full.reset_index(drop=True)
    print(f"  {GREEN}✓ {len(df_full)} velas descargadas{RESET}")

    # ── 2. Análisis de régimen por ventana ─────────────────────────────────────
    print_section("PARTE 1-3: REGIMEN DE MERCADO POR VENTANA")

    regime_data = {}
    for wdef in WF_WINDOWS:
        w = wdef["w"]
        if not analyze_all and w not in windows_to_run:
            regime_data[w] = None
            continue

        ts = wdef["test_start"]
        te = wdef["test_end"]
        # Para el régimen usamos un poco más de contexto (lookback para EMA200)
        lb = WF_CONFIG["lookback"]
        df_test = df_full.iloc[max(0, ts - lb) : te].copy()
        regime = analyze_window_regime(df_test)

        # Fechas reales
        date_start = df_full.iloc[ts]['time'] if 'time' in df_full.columns else "?"
        date_end   = df_full.iloc[te-1]['time'] if 'time' in df_full.columns else "?"
        regime["date_start"] = str(date_start)[:10]
        regime["date_end"]   = str(date_end)[:10]
        regime_data[w] = regime

    # Tabla comparativa (solo ventanas analizadas)
    analyzed = {w: r for w, r in regime_data.items() if r is not None}

    print(f"\n  {'W':>3}  {'PF TEST':>8}  {'WR%':>6}  {'ATR%':>7}  {'ADX':>6}  {'EMA50 SLOPE':>12}  {'REGIME':<18}  {'FECHA TEST'}")
    print(f"  {'─'*88}")

    for w in sorted(analyzed.keys()):
        r   = analyzed[w]
        res = WF_RESULTS[w]
        pf  = res["pf_test"]
        wr  = res["wr_test"]
        col = pf_color(pf)
        rc  = REGIME_COLOR.get(r["regime"], "")
        flag = " ◀ CRITICA" if w in [8, 9] else (" ★ TOP" if w in top2 else "")
        print(f"  {w:>3}  {col}{pf:>8.3f}{RESET}  {wr:>5.1f}%  "
              f"{r['atr_rel_pct']:>6.4f}%  {r['adx_mean']:>6.1f}  "
              f"{r['ema50_slope']:>12.6f}  {rc}{r['regime']:<18}{RESET}  "
              f"{r['date_start']}→{r['date_end']}{flag}")

    # ── 3. Análisis profundo de señales por ventana de foco ───────────────────
    print_section("PARTE 4-5: ANALISIS DE OPERACIONES — VENTANAS CLAVE")

    signals_data = {}
    for w in compare_windows:
        wdef = next((x for x in WF_WINDOWS if x["w"] == w), None)
        if not wdef:
            continue
        label = "CRITICA" if w in [8,9] else ("TOP" if w in top2 else "BOTTOM")
        print(f"\n  [{label}] Ventana {w} — re-ejecutando replay test...")
        sigs = run_window_signals(df_full, wdef)
        sig_analysis = analyze_signals(sigs)
        signals_data[w] = sig_analysis
        res = WF_RESULTS[w]
        r   = regime_data.get(w) or {}

        print(f"    Régimen        : {REGIME_COLOR.get(r.get('regime',''),'')}{r.get('regime','?')}{RESET}")
        print(f"    Fechas test    : {r.get('date_start','?')} → {r.get('date_end','?')}")
        print(f"    PF test (WF)   : {pf_color(res['pf_test'])}{res['pf_test']:.3f}{RESET}  |  WR: {res['wr_test']:.1f}%")
        print(f"    Señales        : {sig_analysis.get('count',0)} totales / {sig_analysis.get('closed',0)} cerradas")
        print(f"    Wins/Losses    : {sig_analysis.get('wins',0)} / {sig_analysis.get('losses',0)}")
        print(f"    Avg win pips   : {GREEN}{sig_analysis.get('avg_win_pips',0):+.1f}{RESET}  |  Avg loss pips: {RED}{sig_analysis.get('avg_loss_pips',0):+.1f}{RESET}")
        print(f"    RR efectivo    : {sig_analysis.get('eff_rr',0):.2f}")
        print(f"    Duración avg   : {sig_analysis.get('dur_avg',0):.1f} velas  "
              f"(min {sig_analysis.get('dur_min',0)} / max {sig_analysis.get('dur_max',0)})")
        if sig_analysis.get('few_large_losses'):
            print(f"    {YELLOW}⚠  Pocas pérdidas grandes (max: {sig_analysis.get('loss_max_pips',0):.1f} pips){RESET}")
        else:
            print(f"    Distribución   : pérdidas homogéneas (std: {sig_analysis.get('loss_std',0):.1f} pips)")
        print(f"    ATR rel%       : {r.get('atr_rel_pct','?'):.4f}%  |  ADX: {r.get('adx_mean','?'):.1f}  |  EMA50 slope: {r.get('ema50_slope','?'):.6f}")

    # ── 4. Comparación top vs bottom ──────────────────────────────────────────
    print_section("PARTE 5: COMPARACION TOP vs BOTTOM")
    print(f"\n  {'W':>3}  {'TYPE':<8}  {'PF TEST':>8}  {'WR%':>6}  {'ATR%':>7}  "
          f"{'ADX':>6}  {'RR EFF':>7}  {'REGIME':<18}")
    print(f"  {'─'*80}")
    for w in sorted(compare_windows):
        r   = regime_data.get(w) or {}
        res = WF_RESULTS[w]
        sa  = signals_data.get(w, {})
        t   = "CRITICA" if w in [8,9] else ("TOP" if w in top2 else "BOTTOM")
        col = pf_color(res["pf_test"])
        rc  = REGIME_COLOR.get(r.get("regime",""), "")
        print(f"  {w:>3}  {t:<8}  {col}{res['pf_test']:>8.3f}{RESET}  "
              f"{res['wr_test']:>5.1f}%  "
              f"{r.get('atr_rel_pct',0):>6.4f}%  "
              f"{r.get('adx_mean',0):>6.1f}  "
              f"{sa.get('eff_rr',0):>7.2f}  "
              f"{rc}{r.get('regime','?'):<18}{RESET}")

    # ── 5. Hipótesis explicativas ─────────────────────────────────────────────
    print_section("PARTE 6: HIPOTESIS EXPLICATIVAS")

    # Extraer datos de ventanas críticas y buenas
    crit_regimes = [regime_data[w]["regime"] for w in [8,9] if regime_data.get(w)]
    crit_adx     = [regime_data[w]["adx_mean"] for w in [8,9] if regime_data.get(w)]
    crit_atr     = [regime_data[w]["atr_rel_pct"] for w in [8,9] if regime_data.get(w)]
    crit_slope   = [abs(regime_data[w]["ema50_slope"]) for w in [8,9] if regime_data.get(w)]

    good_regimes = [regime_data[w]["regime"] for w in top2 if regime_data.get(w)]
    good_adx     = [regime_data[w]["adx_mean"] for w in top2 if regime_data.get(w)]
    good_atr     = [regime_data[w]["atr_rel_pct"] for w in top2 if regime_data.get(w)]
    good_slope   = [abs(regime_data[w]["ema50_slope"]) for w in top2 if regime_data.get(w)]

    hypotheses = []

    # H1: régimen lateral
    if crit_regimes and any(r in ("SIDEWAYS","WEAK_TREND","LOW_VOLATILITY") for r in crit_regimes):
        h1 = {
            "id": "H1",
            "statement": "La estrategia falla en regímenes SIDEWAYS o LOW_VOLATILITY.",
            "evidence": f"Ventanas 8-9 clasificadas como: {crit_regimes}. "
                        f"Ventanas top clasificadas como: {good_regimes}.",
            "supported": True,
        }
        hypotheses.append(h1)
        print(f"\n  {GREEN}H1 — RESPALDADA:{RESET} {h1['statement']}")
        print(f"       Evidencia: {h1['evidence']}")

    # H2: ADX bajo
    avg_crit_adx = np.mean(crit_adx) if crit_adx else 0
    avg_good_adx = np.mean(good_adx) if good_adx else 0
    if avg_crit_adx < avg_good_adx * 0.75:
        h2 = {
            "id": "H2",
            "statement": f"La estrategia falla cuando el ADX es bajo (crit avg: {avg_crit_adx:.1f} vs buenos avg: {avg_good_adx:.1f}).",
            "evidence": f"ADX ventanas 8-9: {[round(x,1) for x in crit_adx]}. ADX ventanas top: {[round(x,1) for x in good_adx]}.",
            "supported": True,
        }
        hypotheses.append(h2)
        print(f"\n  {GREEN}H2 — RESPALDADA:{RESET} {h2['statement']}")
        print(f"       Evidencia: {h2['evidence']}")
    else:
        h2 = {"id":"H2","statement":"ADX bajo no explica las ventanas críticas.","supported":False}
        hypotheses.append(h2)
        print(f"\n  {GRAY}H2 — NO respaldada: ADX similares en críticas y buenas.{RESET}")

    # H3: ATR bajo (baja volatilidad)
    avg_crit_atr = np.mean(crit_atr) if crit_atr else 0
    avg_good_atr = np.mean(good_atr) if good_atr else 0
    if avg_crit_atr < avg_good_atr * 0.80:
        h3 = {
            "id": "H3",
            "statement": f"La estrategia falla en entornos de baja volatilidad (ATR rel crit: {avg_crit_atr:.4f}% vs buenos: {avg_good_atr:.4f}%).",
            "evidence": f"ATR% ventanas 8-9: {[round(x,4) for x in crit_atr]}. ATR% top: {[round(x,4) for x in good_atr]}.",
            "supported": True,
        }
        hypotheses.append(h3)
        print(f"\n  {GREEN}H3 — RESPALDADA:{RESET} {h3['statement']}")
        print(f"       Evidencia: {h3['evidence']}")
    else:
        h3 = {"id":"H3","statement":"ATR similar en ventanas críticas y buenas — volatilidad no es el factor principal.","supported":False}
        hypotheses.append(h3)
        print(f"\n  {GRAY}H3 — NO respaldada: ATR similar en críticas y buenas.{RESET}")

    # H4: pendiente EMA50 plana
    avg_crit_slope = np.mean(crit_slope) if crit_slope else 0
    avg_good_slope = np.mean(good_slope) if good_slope else 0
    if avg_crit_slope < avg_good_slope * 0.50:
        h4 = {
            "id": "H4",
            "statement": f"Pendiente EMA50 plana en ventanas críticas (avg |slope| {avg_crit_slope:.6f} vs buenas {avg_good_slope:.6f}).",
            "evidence": f"Slopes |EMA50| 8-9: {[round(x,6) for x in crit_slope]}. Tops: {[round(x,6) for x in good_slope]}.",
            "supported": True,
        }
        hypotheses.append(h4)
        print(f"\n  {GREEN}H4 — RESPALDADA:{RESET} {h4['statement']}")
        print(f"       Evidencia: {h4['evidence']}")
    else:
        h4 = {"id":"H4","statement":"Pendiente EMA50 no distingue ventanas críticas de buenas.","supported":False}
        hypotheses.append(h4)
        print(f"\n  {GRAY}H4 — NO respaldada: pendientes EMA50 similares.{RESET}")

    # H5: ruido estadístico (pocos trades)
    crit_trades = [WF_RESULTS[w]["test_signals"] for w in [8,9]]
    h5_text = (f"Con solo {crit_trades} trades en ventanas críticas, "
               "el resultado puede ser ruido estadístico.")
    h5 = {"id":"H5","statement":h5_text,"supported": max(crit_trades) < 30 if crit_trades else False}
    hypotheses.append(h5)
    if h5["supported"]:
        print(f"\n  {YELLOW}H5 — POSIBLE:{RESET} {h5_text}")
    else:
        print(f"\n  {GRAY}H5 — Menos probable: suficientes trades en ventanas críticas.{RESET}")

    # ── 6. Tests recomendados ─────────────────────────────────────────────────
    print_section("PARTE 7: TESTS ADICIONALES RECOMENDADOS")

    supported_hs = [h for h in hypotheses if h.get("supported")]
    rank = 1
    for h in supported_hs:
        hid = h["id"]
        if hid == "H1":
            print(f"\n  Test {rank} (de H1) — Filtro de régimen")
            print(f"    Clasificar cada barra como TREND/SIDEWAYS antes de entrar.")
            print(f"    Métrica: % de velas que el ADX < 20 en las últimas 48h.")
            print(f"    Simular: operar solo cuando ADX > 20 en la entrada.")
            print(f"    Esperado: reducir trades en ventanas 8-9, mantener buenas.")
            rank += 1
        if hid == "H2":
            print(f"\n  Test {rank} (de H2) — Umbral ADX en entrada")
            print(f"    Simular tres umbrales: ADX > 15 / ADX > 20 / ADX > 25.")
            print(f"    Medir: cambio en PF, WR, número de señales por ventana.")
            print(f"    Riesgo: ADX > 25 puede reducir demasiado las señales.")
            rank += 1
        if hid == "H3":
            print(f"\n  Test {rank} (de H3) — Filtro ATR mínimo")
            print(f"    Excluir entradas cuando ATR < percentil 25 de los últimos 100 periodos.")
            print(f"    Simular: ATR < 0.5x media_20 → no entrar.")
            print(f"    Esperado: eliminar entradas en compresiones de volatilidad.")
            rank += 1
        if hid == "H4":
            print(f"\n  Test {rank} (de H4) — Filtro pendiente EMA50")
            print(f"    Operar solo cuando |pendiente EMA50| > umbral mínimo.")
            print(f"    Umbrales a probar: 0.0001, 0.0002, 0.0003 por barra.")
            rank += 1

    print(f"\n  Test {rank} — Backtest separado por régimen clasificado")
    print(f"    Clasificar todas las velas del histórico por régimen (SIDEWAYS/WEAK/STRONG).")
    print(f"    Ejecutar backtest solo en cada subconjunto.")
    print(f"    Objetivo: confirmar en qué régimen la estrategia tiene edge real.")

    # ── 7. Conclusión y decisión ──────────────────────────────────────────────
    print_section("PARTE 8: CONCLUSION Y DECISION")

    n_supported = len(supported_hs)
    regime_issue = any(h["id"] in ("H1","H2","H3","H4") for h in supported_hs)

    if regime_issue:
        cause = "B) Cambio de régimen + C/D) Falta de filtro de tendencia/volatilidad"
        recommendation = "Diseñar experimento específico"
        detail = (
            "Los datos respaldan que las ventanas 8-9 corresponden a un régimen de mercado\n"
            "  diferente al de las ventanas ganadoras. La estrategia tiene edge en tendencias\n"
            "  claras pero falla en mercados sin dirección. Esto NO es overfitting — es un\n"
            "  problema de definición de régimen operativo.\n\n"
            "  Próximo paso recomendado: backtest clasificado por régimen (Test 4 arriba).\n"
            "  Si confirma el patrón → añadir filtro ADX/ATR como experimento separado.\n"
            "  NO modificar la estrategia todavía — primero confirmar la hipótesis de régimen."
        )
    else:
        cause = "E) Ruido estadístico normal"
        recommendation = "Continuar validación"
        detail = "Insuficiente diferencia estructural entre ventanas críticas y buenas para identificar causa."

    print(f"\n  Causa principal identificada : {BOLD}{cause}{RESET}")
    print(f"  Recomendación               : {BOLD}{recommendation}{RESET}")
    print(f"\n  Justificación:")
    print(f"  {detail}")

    # ── 8. Guardar resultado ──────────────────────────────────────────────────
    if args.save:
        output = {
            "investigation_date":  datetime.now().strftime("%Y-%m-%d"),
            "hypothesis_id":       "eurusd_simple",
            "wf_run_id":           "walk_forward_20260604_eurusd_simple",
            "focus_windows":       focus_windows,
            "regime_data":         {str(w): r for w, r in analyzed.items()},
            "signals_analysis":    {str(w): s for w, s in signals_data.items()},
            "hypotheses":          hypotheses,
            "conclusion": {
                "cause":          cause,
                "recommendation": recommendation,
            },
        }
        out_path = (Path(__file__).parent.parent / "run_cards" /
                    f"RC_investigation_windows89_{datetime.now().strftime('%Y%m%d')}.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n  {GREEN}✓ Resultado guardado: {out_path}{RESET}")

    print(f"\n{'═'*72}\n")


if __name__ == "__main__":
    main()
