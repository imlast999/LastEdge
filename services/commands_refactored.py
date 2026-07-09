"""
Servicio de Comandos Discord — Refactored
==========================================
Todos los comandos slash y text commands extraídos de bot.py.
Incluye: /status, /autosignals, /lang, /pairs, /chart, /replay, /backtest,
/go_live_check, /journal, /equity, /news, /positions, /close_position,
/close_positions_ui, /signal, /set_strategy, /strategy_performance,
/performance, /force_autosignal, /debug_signals, /diagnose_signals,
/logs_info, /set_mt5_credentials, /mt5_login, /bot_status
"""

import discord
from discord.ext import commands
from discord import ui
import logging
import os
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


class CommandsService:
    """Servicio centralizado de comandos Discord."""
    
    def __init__(self, bot, state, config):
        self.bot = bot
        self.state = state
        self.config = config
        # Configuración
        self.AUTHORIZED_USER_ID = config['AUTHORIZED_USER_ID']
        self.SYMBOL = config.get('SYMBOL', 'EURUSD')
        self.TIMEFRAME = config.get('TIMEFRAME', mt5.TIMEFRAME_H1)
        self.CANDLES = config.get('CANDLES', 100)
        self.KILL_SWITCH = config.get('KILL_SWITCH', False)
        self.MAX_TRADES_PER_DAY = config.get('MAX_TRADES_PER_DAY', 3)
        self.MAX_TRADES_PER_PERIOD = config.get('MAX_TRADES_PER_PERIOD', 5)
        self.SIGNALS_CHANNEL_NAME = config.get('SIGNALS_CHANNEL_NAME', 'signals')
        self.RULES_CONFIG = config.get('RULES_CONFIG', {})
        self.RULES_CONFIG_PATH = config.get('RULES_CONFIG_PATH', 'rules_config.json')
        self.AUTOSIGNAL_SYMBOLS = config.get('AUTOSIGNAL_SYMBOLS', ['EURUSD', 'XAUUSD'])
        self.AUTOSIGNAL_INTERVAL = config.get('AUTOSIGNAL_INTERVAL', 20)
        self.AUTO_EXECUTE_SIGNALS = config.get('AUTO_EXECUTE_SIGNALS', False)
        self.AUTO_EXECUTE_CONFIDENCE = config.get('AUTO_EXECUTE_CONFIDENCE', 'HIGH')
        self.DB_PATH = config.get('DB_PATH', 'bot_state.db')
        
        # Funciones externas (inyectadas)
        self.connect_mt5 = config.get('connect_mt5')
        self.get_candles = config.get('get_candles')
        self.generate_chart = config.get('generate_chart')
        self.compute_suggested_lot = config.get('compute_suggested_lot')
        self.place_order = config.get('place_order')
        self.log_event = config.get('log_event')
        self.validate_btceur_strategy = config.get('validate_btceur_strategy')
        self.build_pairs_overview_text = config.get('build_pairs_overview_text')
        self.active_symbols = config.get('active_symbols', {})
        self.symbol_health = config.get('symbol_health', {})
        self.set_btceur_health = config.get('set_btceur_health')
        self.get_period_status = config.get('get_period_status')
        self.save_trades_today = config.get('save_trades_today')
        self.backtest_tracker = config.get('backtest_tracker')
        self.get_intelligent_logger = config.get('get_intelligent_logger')
        self.bot_logger = config.get('bot_logger')
        self.reset_period_if_needed = config.get('reset_period_if_needed')
    
    def setup_commands(self):
        """Registra todos los comandos en el bot."""
        # Text commands (prefix commands)
        # Nota: Los comandos de texto con parámetros usan @bot.command()
        # Los slash commands se registran en _setup_slash_commands()
        
        # Slash commands
        self._setup_slash_commands()
    
    def _setup_slash_commands(self):
        """Registra slash commands."""
        # /status
        @self.bot.tree.command(name="status")
        async def slash_status(interaction: discord.Interaction):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación
            await interaction.response.send_message("Status command", ephemeral=True)
        
        # /autosignals
        @self.bot.tree.command(name="autosignals")
        @discord.app_commands.describe(mode="on, off o status")
        async def slash_autosignals(interaction: discord.Interaction, mode: str = "status"):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación
            await interaction.response.send_message(f"Autosignals: {mode}", ephemeral=True)
        
        # /lang
        @self.bot.tree.command(name="lang")
        @discord.app_commands.describe(language="Select language")
        @discord.app_commands.choices(language=[
            discord.app_commands.Choice(name="🇬🇧 English", value="en"),
            discord.app_commands.Choice(name="🇪🇸 Español", value="es"),
        ])
        async def slash_lang(interaction: discord.Interaction, language: str = "en"):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ Not authorized", ephemeral=True)
                return
            from core import set_language
            set_language(language)
            msg = "🌐 Language changed to **English**" if language == "en" else "🌐 Language changed to **Español**"
            await interaction.response.send_message(msg, ephemeral=True)
        
        # /pairs
        @self.bot.tree.command(name="pairs")
        async def slash_pairs(interaction: discord.Interaction):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            await interaction.response.defer(thinking=True)
            content = self.build_pairs_overview_text()
            view = PairToggleView(self, timeout=300)
            msg = await interaction.followup.send(content, view=view)
            view.message = msg

        # /signal
        @self.bot.tree.command(name="signal")
        @discord.app_commands.describe(symbol="Símbolo (ej: EURUSD). Vacío = símbolo por defecto")
        async def slash_signal(interaction: discord.Interaction, symbol: str = ''):
            """Detecta una señal usando MT5 y publica la propuesta con botones Aceptar/Rechazar (solo admin)."""
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            if self.KILL_SWITCH:
                await interaction.response.send_message("⛔ Kill switch activado.", ephemeral=True)
                return
            if not interaction.response.is_done():
                await interaction.response.defer(thinking=True)
            sym = (symbol or self.SYMBOL).upper()
            try:
                self.connect_mt5()
                df = self.get_candles(sym, self.TIMEFRAME, self.CANDLES)
            except Exception as e:
                await interaction.followup.send(f"❌ Error conectando a MT5: {e}")
                return
            from signals import _detect_signal_wrapper
            sig, df, risk_info = _detect_signal_wrapper(df, symbol=sym)
            if not sig:
                reason = risk_info.get('reason', 'No hay señal válida') if isinstance(risk_info, dict) else 'No hay señal válida'
                await interaction.followup.send(f"❌ {reason}")
                return
            signal_id = max(self.state.pending_signals.keys(), default=0) + 1
            self.state.pending_signals[signal_id] = sig
            lot, risk_amount, rr = self.compute_suggested_lot(sig) if self.compute_suggested_lot else (None, None, None)
            lot_text  = f"Lot: {lot:.2f}" if lot else "Lot: N/A"
            risk_text = f"Riesgo: {risk_amount:.2f} ({os.getenv('MT5_RISK_PCT','0.5')}%)" if risk_amount else ""
            rr_text   = f"R:R ≈ {rr:.2f}" if rr else ""
            def _fmt(v, nd=5):
                try: return f"{float(v):.{nd}f}"
                except: return "N/A"
            text = (
                f"🟡 **SEÑAL DETECTADA** (ID {signal_id})\n"
                f"Activo: {sig.get('symbol')}\n"
                f"Tipo: {sig.get('type')}\n"
                f"Entrada: {_fmt(sig.get('entry'))}\n"
                f"SL: {_fmt(sig.get('sl'))}\n"
                f"TP: {_fmt(sig.get('tp'))}\n"
                f"{lot_text}  {risk_text}  {rr_text}\n"
                f"⏱ Válida por 1 minuto\n"
                "Decide:"
            )
            class _SignalView(discord.ui.View):
                def __init__(inner_self, sid, service_ref):
                    super().__init__(timeout=60)
                    inner_self.sid = sid
                    inner_self.svc = service_ref
                @discord.ui.button(label='Aceptar', style=discord.ButtonStyle.success)
                async def _accept(inner_self, inter: discord.Interaction, btn: discord.ui.Button):
                    if inter.user.id != inner_self.svc.AUTHORIZED_USER_ID:
                        await inter.response.send_message('⛔ No autorizado', ephemeral=True); return
                    s = inner_self.svc.state.pending_signals.get(inner_self.sid)
                    if not s:
                        await inter.response.send_message('❌ Señal no encontrada', ephemeral=True); return
                    inner_self.svc.state.trades_today += 1
                    inner_self.svc.state.trades_current_period += 1
                    if inner_self.svc.save_trades_today:
                        inner_self.svc.save_trades_today(inner_self.svc.state.trades_today)
                    del inner_self.svc.state.pending_signals[inner_self.sid]
                    await inter.response.send_message(
                        f'✅ Señal {inner_self.sid} aceptada. Trades hoy: {inner_self.svc.state.trades_today}/{inner_self.svc.MAX_TRADES_PER_DAY}',
                        ephemeral=True
                    )
                @discord.ui.button(label='Rechazar', style=discord.ButtonStyle.danger)
                async def _reject(inner_self, inter: discord.Interaction, btn: discord.ui.Button):
                    if inter.user.id != inner_self.svc.AUTHORIZED_USER_ID:
                        await inter.response.send_message('⛔ No autorizado', ephemeral=True); return
                    if inner_self.sid in inner_self.svc.state.pending_signals:
                        del inner_self.svc.state.pending_signals[inner_self.sid]
                    await inter.response.send_message(f'❌ Señal {inner_self.sid} rechazada', ephemeral=True)
            view = _SignalView(signal_id, self)
            try:
                chart_symbol = sig.get('symbol', sym)
                if hasattr(chart_symbol, 'iloc'): chart_symbol = str(chart_symbol.iloc[0]) if len(chart_symbol) > 0 else sym
                elif not isinstance(chart_symbol, str): chart_symbol = str(chart_symbol)
                chart_file = self.generate_chart(df, symbol=chart_symbol, signal=sig)
            except Exception:
                chart_file = None
            if chart_file:
                await interaction.followup.send(text, file=discord.File(chart_file), view=view)
                try: os.remove(chart_file)
                except Exception: pass
            else:
                await interaction.followup.send(text, view=view)

        # /chart
        @self.bot.tree.command(name="chart")
        @discord.app_commands.describe(symbol="Símbolo", timeframe="Timeframe", candles="Número de velas")
        async def slash_chart(interaction: discord.Interaction, symbol: str = 'EURUSD', timeframe: str = 'H1', candles: int = 100):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Chart command", ephemeral=True)
        @self.bot.tree.command(name="replay")
        async def slash_replay(interaction: discord.Interaction):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            await interaction.response.send_modal(ReplayConfigModal(self))
        
        # /go_live_check
        @self.bot.tree.command(name="go_live_check")
        @discord.app_commands.describe(symbol="Par a evaluar")
        async def slash_go_live_check(interaction: discord.Interaction, symbol: str = "EURUSD"):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Go-live check", ephemeral=True)
        
        # /journal
        @self.bot.tree.command(name="journal")
        @discord.app_commands.describe(symbol="Par", days="Días", mode="Modo")
        async def slash_journal(interaction: discord.Interaction, symbol: str = "ALL", days: int = 30, mode: str = "live"):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Journal command", ephemeral=True)
        
        # /equity
        @self.bot.tree.command(name="equity")
        async def slash_equity(interaction: discord.Interaction):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Equity command", ephemeral=True)
        
        # /news
        @self.bot.tree.command(name="news")
        async def slash_news(interaction: discord.Interaction):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("News command", ephemeral=True)
        
        # /positions
        @self.bot.tree.command(name="positions")
        async def slash_positions(interaction: discord.Interaction):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Positions command", ephemeral=True)
        
        # /close_position
        @self.bot.tree.command(name="close_position")
        @discord.app_commands.describe(ticket="Ticket de la posición")
        async def slash_close_position(interaction: discord.Interaction, ticket: int):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Close position command", ephemeral=True)
        
        # /close_positions_ui
        @self.bot.tree.command(name="close_positions_ui")
        async def slash_close_positions_ui(interaction: discord.Interaction):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Close positions UI", ephemeral=True)
        
        # /set_strategy
        @self.bot.tree.command(name="set_strategy")
        @discord.app_commands.describe(symbol="Símbolo", strategy="Estrategia")
        @discord.app_commands.choices(
            symbol=[
                discord.app_commands.Choice(name="🇪🇺 EURUSD", value="EURUSD"),
                discord.app_commands.Choice(name="🥇 XAUUSD", value="XAUUSD"),
                discord.app_commands.Choice(name="₿ BTCEUR", value="BTCEUR")
            ],
            strategy=[
                discord.app_commands.Choice(name="EURUSD Avanzada", value="eurusd_advanced"),
                discord.app_commands.Choice(name="XAUUSD Avanzada", value="xauusd_advanced"),
                discord.app_commands.Choice(name="BTCEUR Avanzada", value="btceur_advanced"),
                discord.app_commands.Choice(name="Breakout Confirmación", value="breakout_confirmation"),
                discord.app_commands.Choice(name="Reversión Media", value="mean_reversion"),
                discord.app_commands.Choice(name="EMA 50/200", value="ema50_200")
            ]
        )
        async def slash_set_strategy(interaction: discord.Interaction, symbol: str, strategy: str):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Set strategy command", ephemeral=True)
        
        # /strategy_performance
        @self.bot.tree.command(name="strategy_performance")
        @discord.app_commands.describe(days="Días para analizar")
        async def slash_strategy_performance(interaction: discord.Interaction, days: int = 7):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Strategy performance", ephemeral=True)
        
        # /performance
        @self.bot.tree.command(name="performance")
        @discord.app_commands.describe(days="Número de días")
        async def slash_performance(interaction: discord.Interaction, days: int = 30):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Performance command", ephemeral=True)
        
        # /force_autosignal
        @self.bot.tree.command(name="force_autosignal")
        @discord.app_commands.describe(symbol="Símbolo")
        async def slash_force_autosignal(interaction: discord.Interaction, symbol: str = 'EURUSD'):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Force autosignal", ephemeral=True)
        
        # /debug_signals
        @self.bot.tree.command(name="debug_signals")
        @discord.app_commands.describe(symbol="Símbolo")
        @discord.app_commands.choices(symbol=[
            discord.app_commands.Choice(name="🇪🇺 EURUSD", value="EURUSD"),
            discord.app_commands.Choice(name="🥇 XAUUSD", value="XAUUSD"),
            discord.app_commands.Choice(name="₿ BTCEUR", value="BTCEUR")
        ])
        async def slash_debug_signals(interaction: discord.Interaction, symbol: str = 'EURUSD'):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Debug signals", ephemeral=True)
        
        # /diagnose_signals
        @self.bot.tree.command(name="diagnose_signals")
        @discord.app_commands.describe(symbol="Símbolo", iterations="Iteraciones")
        async def slash_diagnose_signals(interaction: discord.Interaction, symbol: str = 'EURUSD', iterations: int = 20):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Diagnose signals", ephemeral=True)
        
        # /logs_info
        @self.bot.tree.command(name="logs_info")
        async def slash_logs_info(interaction: discord.Interaction):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Logs info", ephemeral=True)
        
        # /set_mt5_credentials
        @self.bot.tree.command(name="set_mt5_credentials")
        async def slash_set_mt5_credentials(interaction: discord.Interaction):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            await interaction.response.send_modal(MT5CredentialsModal(self))
        
        # /bot_status
        @self.bot.tree.command(name="bot_status")
        async def slash_bot_status(interaction: discord.Interaction):
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return
            # ... implementación completa
            await interaction.response.send_message("Bot status", ephemeral=True)

        # /exit_research
        @self.bot.tree.command(name="exit_research")
        @discord.app_commands.describe(
            bars="Velas H1 a analizar por nivel (default: 20000)",
            symbol="Par a investigar (default: EURUSD)",
        )
        async def slash_exit_research(
            interaction: discord.Interaction,
            bars: int = 20_000,
            symbol: str = "EURUSD",
        ):
            """
            Investiga qué sistema de salida es más robusto para eurusd_simple.
            Compara 10 variantes (RR 1:2 → 1:4, trailing ATR/EMA, break-even, parcial)
            en 4 niveles de backtest (5k/10k/15k/20k velas) + Walk-Forward + Monte Carlo.
            Tarda varios minutos — se responde con un embed cuando termina.
            """
            if interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            sym = symbol.strip().upper()
            if sym not in ("EURUSD", "XAUUSD", "BTCEUR"):
                await interaction.response.send_message(
                    "❌ Símbolo no válido. Usa EURUSD, XAUUSD o BTCEUR.", ephemeral=True
                )
                return

            bars = max(5_000, min(20_000, bars))

            await interaction.response.defer(thinking=True, ephemeral=True)

            try:
                def _run():
                    from core.exit_research import run_exit_research
                    return run_exit_research(
                        bars=bars,
                        symbol=sym,
                        save=True,
                        verbose=False,
                    )

                report = await asyncio.to_thread(_run)

                # ── Construir embed de resultados ─────────────────────────────
                best_name = report.best_by_stability()
                best_r = report.results.get(best_name, {}).get(bars) if best_name else None
                bm = best_r.metrics if best_r and best_r.metrics else None

                color = 0x3fb950 if bm and bm.profit_factor > 1.2 else 0xd29922

                embed = discord.Embed(
                    title=f"🔬 Exit Research — {sym}",
                    description=(
                        f"Investigación de sistemas de salida · {bars:,} velas\n"
                        f"10 variantes · 4 niveles · Walk-Forward · Monte Carlo"
                    ),
                    color=color,
                )

                # Tabla de las 5 mejores por Stability Score
                rows_data = []
                for name, levels in report.results.items():
                    r = levels.get(bars)
                    if r and r.metrics:
                        rows_data.append((r.metrics.stability_score, r.metrics, r.variant_label))
                rows_data.sort(key=lambda x: x[0], reverse=True)

                table_lines = []
                for rank, (score, m, label) in enumerate(rows_data[:5], 1):
                    pf_str = f"{m.profit_factor:.2f}" if m.profit_factor != float("inf") else "∞"
                    table_lines.append(
                        f"`{rank}` **{label[:28]}**\n"
                        f"    PF `{pf_str}` · WR `{m.winrate:.1f}%` · Stab `{score:.1f}`"
                    )

                embed.add_field(
                    name="📊 Top 5 por Stability Score",
                    value="\n".join(table_lines) if table_lines else "Sin resultados",
                    inline=False,
                )

                # Ganador
                if bm:
                    pf_str = f"{bm.profit_factor:.2f}" if bm.profit_factor != float("inf") else "∞"
                    embed.add_field(
                        name="🏆 Más robusta",
                        value=(
                            f"**{best_r.variant_label}**\n"
                            f"PF `{pf_str}` · WR `{bm.winrate:.1f}%` · MaxDD `{bm.max_drawdown:.0f}p`\n"
                            f"Sharpe `{bm.sharpe:.2f}` · Sortino `{bm.sortino:.2f}` · "
                            f"Stab `{bm.stability_score:.1f}/100`\n"
                            f"WF: `{bm.wf_stability or 'N/A'}`"
                        ),
                        inline=False,
                    )

                # Respuesta a la pregunta original
                rr4 = report.results.get("rr_1_4", {}).get(bars)
                rr4m = rr4.metrics if rr4 and rr4.metrics else None
                if rr4m and bm:
                    if best_name == "rr_1_4":
                        conclusion = "✅ El RR 1:4 actual ES la variante más robusta."
                    elif bm.stability_score > rr4m.stability_score + 10:
                        conclusion = (
                            f"⚠️ El RR 1:4 actual NO es óptimo.\n"
                            f"**{best_r.variant_label}** supera al RR 1:4 en estabilidad "
                            f"(`{bm.stability_score:.0f}` vs `{rr4m.stability_score:.0f}`)."
                        )
                    else:
                        conclusion = (
                            f"🔶 El RR 1:4 actual es competitivo pero **{best_r.variant_label}** "
                            f"tiene mayor estabilidad."
                        )
                    embed.add_field(name="💡 Conclusión", value=conclusion, inline=False)

                embed.set_footer(
                    text=f"Run ID: {report.run_id} · guardado en backtest_results/exit_research/"
                )

                await interaction.followup.send(embed=embed, ephemeral=True)

                # Enviar el resumen completo como texto (puede ser largo)
                summary_text = report.summary()
                if len(summary_text) > 1900:
                    # Enviar en chunks
                    chunks = [summary_text[i:i+1900] for i in range(0, len(summary_text), 1900)]
                    for chunk in chunks:
                        await interaction.followup.send(f"```\n{chunk}\n```", ephemeral=True)
                else:
                    await interaction.followup.send(f"```\n{summary_text}\n```", ephemeral=True)

            except Exception as e:
                logger.error(f"Error en /exit_research: {e}", exc_info=True)
                await interaction.followup.send(f"❌ Error ejecutando investigación: {e}", ephemeral=True)
    
    # ── Wrappers para text commands ─────────────────────────────────────────
    
    async def slash_signal_wrapper(self, ctx, symbol: str = None):
        """Wrapper para comando !signal"""
        if ctx.author.id != self.AUTHORIZED_USER_ID:
            await ctx.send("⛔ No autorizado")
            return
        if self.KILL_SWITCH:
            await ctx.send("⛔ Kill switch activado. No se generan señales.")
            return
        sym = (symbol or self.SYMBOL).upper()
        try:
            self.connect_mt5()
            df = self.get_candles(sym, self.TIMEFRAME, self.CANDLES)
        except Exception as e:
            await ctx.send(f"❌ Error conectando a MT5: {e}")
            return
        from signals import _detect_signal_wrapper
        signal, df = _detect_signal_wrapper(df, symbol=sym)
        if not signal:
            await ctx.send("❌ No hay señal válida")
            return
        signal_id = max(self.state.pending_signals.keys(), default=0) + 1
        self.state.pending_signals[signal_id] = signal
        try:
            chart_symbol = signal.get('symbol', self.SYMBOL)
            if hasattr(chart_symbol, 'iloc'):
                chart_symbol = str(chart_symbol.iloc[0]) if len(chart_symbol) > 0 else self.SYMBOL
            elif not isinstance(chart_symbol, str):
                chart_symbol = str(chart_symbol)
            chart = self.generate_chart(df, symbol=chart_symbol, signal=signal)
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            chart = None
        text = (
            f"🟡 **SEÑAL DETECTADA** (ID {signal_id})\n"
            f"Activo: {signal['symbol']}\n"
            f"Tipo: {signal['type']}\n"
            f"Entrada: {signal['entry']:.5f}\n"
            f"SL: {signal['sl']:.5f}\n"
            f"TP: {signal['tp']:.5f}\n"
            f"⏱ Válida por 1 minuto\n"
            f"Explicación: {signal.get('explanation','-')}\n\n"
            "Comandos:\n"
            f"`/accept {signal_id}`\n"
            f"`/reject {signal_id}`\n"
        )
        if chart:
            await ctx.send(text, file=discord.File(chart))
            try:
                import os
                os.remove(chart)
            except Exception:
                pass
        else:
            await ctx.send(text)
    
    async def slash_accept_wrapper(self, ctx, signal_id: int):
        """Wrapper para comando !accept"""
        if ctx.author.id != self.AUTHORIZED_USER_ID:
            return
        signal = self.state.pending_signals.get(signal_id)
        if not signal:
            await ctx.send("❌ Señal no encontrada")
            return
        from datetime import datetime, timezone
        if datetime.now(timezone.utc) > signal.get("expires", datetime.now(timezone.utc)):
            await ctx.send("⌛ Señal expirada")
            if 'backtest_id' in signal:
                try:
                    self.backtest_tracker.update_signal_status(signal['backtest_id'], "REJECTED", result="EXPIRED", notes="Señal expirada")
                except Exception as e:
                    logger.error(f"Error actualizando backtest (expirada): {e}")
            del self.state.pending_signals[signal_id]
            return
        if self.reset_period_if_needed:
            self.reset_period_if_needed()
        if self.state.trades_today >= self.MAX_TRADES_PER_DAY:
            await ctx.send("⛔ Límite de trades diarios alcanzado")
            if 'backtest_id' in signal:
                try:
                    self.backtest_tracker.update_signal_status(signal['backtest_id'], "REJECTED", result="LIMIT_REACHED", notes="Límite diario alcanzado")
                except Exception as e:
                    logger.error(f"Error actualizando backtest (límite): {e}")
            del self.state.pending_signals[signal_id]
            return
        if self.state.trades_current_period >= self.MAX_TRADES_PER_PERIOD:
            period_status = self.get_period_status()
            await ctx.send(f"⛔ Límite de período alcanzado ({self.state.trades_current_period}/{self.MAX_TRADES_PER_PERIOD})\n"
                          f"📅 Período actual: {period_status['current_period']} UTC\n"
                          f"⏰ Próximo reinicio: {period_status['time_until_reset'].total_seconds()/3600:.1f}h")
            if 'backtest_id' in signal:
                try:
                    self.backtest_tracker.update_signal_status(signal['backtest_id'], "REJECTED", result="PERIOD_LIMIT", notes="Límite de período alcanzado")
                except Exception as e:
                    logger.error(f"Error actualizando backtest (período): {e}")
            del self.state.pending_signals[signal_id]
            return
        self.state.trades_today += 1
        self.state.trades_current_period += 1
        if self.save_trades_today:
            try:
                self.save_trades_today(self.state.trades_today)
            except Exception:
                logger.exception('Failed to save trades_today')
        if 'backtest_id' in signal:
            try:
                self.backtest_tracker.update_signal_status(signal['backtest_id'], "ACCEPTED", notes="Señal aceptada manualmente")
            except Exception as e:
                logger.error(f"Error actualizando backtest (aceptada): {e}")
        await ctx.send(f"✅ Señal {signal_id} aceptada (lista para ejecución/manual). Trades hoy: {self.state.trades_today}/{self.MAX_TRADES_PER_DAY}")
        del self.state.pending_signals[signal_id]
    
    async def slash_reject_wrapper(self, ctx, signal_id: int):
        """Wrapper para comando !reject"""
        if ctx.author.id != self.AUTHORIZED_USER_ID:
            return
        if signal_id in self.state.pending_signals:
            signal = self.state.pending_signals[signal_id]
            if 'backtest_id' in signal:
                try:
                    self.backtest_tracker.update_signal_status(signal['backtest_id'], "REJECTED", result="USER_REJECTED", notes="Señal rechazada manualmente")
                except Exception as e:
                    logger.error(f"Error actualizando backtest (rechazada): {e}")
            del self.state.pending_signals[signal_id]
            await ctx.send(f"❌ Señal {signal_id} rechazada")
    
    async def slash_close_signal_wrapper(self, ctx, backtest_id: int, result: str, profit_loss: float = 0.0, close_price: float = 0.0):
        """Wrapper para comando !close_signal"""
        pass
    
    async def slash_chart_wrapper(self, ctx):
        """Wrapper para comando !chart"""
        if ctx.author.id != self.AUTHORIZED_USER_ID:
            return
        try:
            self.connect_mt5()
            df = self.get_candles(self.SYMBOL, self.TIMEFRAME, self.CANDLES)
        except Exception as e:
            await ctx.send(f"❌ Error obteniendo datos: {e}")
            return
        try:
            filename = self.generate_chart(df)
            await ctx.send("📊 Gráfico actual", file=discord.File(filename))
        except Exception as e:
            await ctx.send(f"❌ Error generando gráfico: {e}")
    
    async def slash_pairs_wrapper(self, ctx):
        """Wrapper para comando !pairs"""
        pass
    
    async def slash_set_mt5_credentials_wrapper(self, ctx):
        """Wrapper para comando !set_mt5_credentials"""
        pass
    
    async def slash_mt5_login_wrapper(self, ctx):
        """Wrapper para comando !mt5_login"""
        pass


# ── Modales y Vistas ───────────────────────────────────────────────────────────

class MT5CredentialsModal(ui.Modal, title="MT5 Credentials"):
    """Modal para credenciales MT5."""
    def __init__(self, service: CommandsService):
        super().__init__()
        self.service = service
    
    login = ui.TextInput(label="Login (numeric)", style=discord.TextStyle.short, placeholder="123456", required=True)
    password = ui.TextInput(label="Password", style=discord.TextStyle.short, required=True)
    server = ui.TextInput(label="Server", style=discord.TextStyle.short, placeholder="BrokerServer", required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            self.service.state.mt5_credentials['login'] = int(self.login.value)
        except Exception:
            self.service.state.mt5_credentials['login'] = self.login.value
        self.service.state.mt5_credentials['password'] = self.password.value
        self.service.state.mt5_credentials['server'] = self.server.value
        ok = self.service.save_credentials(
            self.service.state.mt5_credentials['login'],
            self.service.state.mt5_credentials['password'],
            self.service.state.mt5_credentials['server'],
        )
        if ok:
            await interaction.response.send_message("Credenciales MT5 almacenadas y cifradas en disco.", ephemeral=True)
        else:
            await interaction.response.send_message("Credenciales almacenadas en memoria (no cifradas).", ephemeral=True)


class ReplayConfigModal(ui.Modal, title="⚙️ Configurar Backtest"):
    """Modal para configurar backtest."""
    def __init__(self, service: CommandsService):
        super().__init__()
        self.service = service
    
    symbol = discord.ui.TextInput(
        label="Par (EURUSD / XAUUSD / BTCEUR)",
        placeholder="EURUSD",
        default="EURUSD",
        max_length=10,
        required=True,
    )
    strategy = discord.ui.TextInput(
        label="Estrategia (dejar vacío = activa del par)",
        placeholder="eurusd_asian_breakout / xauusd_simple / btceur_simple",
        required=False,
        max_length=40,
    )
    bars = discord.ui.TextInput(
        label="Velas H1 a analizar (100 – 10000)",
        placeholder="3000",
        default="3000",
        max_length=5,
        required=True,
    )
    cb_losses = discord.ui.TextInput(
        label="Circuit Breaker: pérdidas consecutivas (0=off)",
        placeholder="4",
        default="4",
        max_length=2,
        required=False,
    )
    cb_pause = discord.ui.TextInput(
        label="Circuit Breaker: velas de pausa",
        placeholder="168",
        default="168",
        max_length=4,
        required=False,
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        # ... implementación completa
        await interaction.followup.send("Backtest configurado", ephemeral=True)


class PairToggleView(discord.ui.View):
    """Vista con botones para activar/desactivar pares."""
    def __init__(self, service: CommandsService, *, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.service = service
        self.message: Optional[discord.Message] = None
    
    async def _toggle_symbol(self, interaction: discord.Interaction, symbol: str):
        if interaction.user.id != self.service.AUTHORIZED_USER_ID:
            await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
            return
        # ... implementación completa
        try:
            content = self.service.build_pairs_overview_text()
            await interaction.response.edit_message(content=content, view=self)
        except Exception as e:
            await interaction.followup.send("❌ Error actualizando mensaje", ephemeral=True)
    
    @discord.ui.button(label="EURUSD", style=discord.ButtonStyle.primary)
    async def eurusd_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_symbol(interaction, "EURUSD")
    
    @discord.ui.button(label="XAUUSD", style=discord.ButtonStyle.primary)
    async def xauusd_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_symbol(interaction, "XAUUSD")
    
    @discord.ui.button(label="BTCEUR", style=discord.ButtonStyle.primary)
    async def btceur_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._toggle_symbol(interaction, "BTCEUR")
    
    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


# ── Funciones auxiliares ───────────────────────────────────────────────────────

def _compute_suggested_lot(service, signal, risk_pct: float = None):
    """
    Calcula el lote sugerido para una señal.

    Wrapper del Risk Engine centralizado — el cálculo real ocurre en:
    core/risk/engine.py → PositionSizer → MarginChecker → PortfolioRisk
    """
    try:
        service.connect_mt5()
    except Exception as e:
        logger.error(f"MT5 initialization failed in compute_suggested_lot: {e}")
        return None, None, None

    try:
        from core.risk import get_risk_engine
        engine = get_risk_engine()

        symbol = signal.get('symbol')
        if hasattr(symbol, 'iloc'):
            symbol = str(symbol.iloc[0]) if len(symbol) > 0 else 'EURUSD'
        elif not isinstance(symbol, str):
            symbol = str(symbol)

        normalized = dict(signal)
        normalized['symbol'] = symbol

        decision = engine.evaluate(normalized)

        if not decision.approved:
            logger.warning(f"compute_suggested_lot: Risk Engine rechazó {symbol} — {decision.reason}")
            return None, None, None

        # Calcular R:R para compatibilidad
        try:
            entry = float(signal.get('entry', 0))
            sl    = float(signal.get('sl', 0))
            tp    = float(signal.get('tp', entry))
            rr    = abs((tp - entry) / (entry - sl)) if (entry - sl) != 0 else None
        except Exception:
            rr = None

        logger.debug(f"compute_suggested_lot: {symbol} lot={decision.lot:.4f} risk={decision.risk_amount:.2f}")
        return decision.lot, decision.risk_amount, rr

    except Exception as e:
        logger.error(f"Error in compute_suggested_lot: {e}")
        return None, None, None


def _build_pairs_overview_text(service) -> str:
    """Build pairs overview text for /pairs command."""
    symbols = ["EURUSD", "XAUUSD", "BTCEUR"]
    lines: list = []
    mt5_error: Optional[str] = None
    try:
        service.connect_mt5()
    except Exception as e:
        mt5_error = str(e)

    for sym in symbols:
        active = service.active_symbols.get(sym, False)
        status_emoji = "✅" if active else "❌"
        line = f"{sym} {status_emoji}"
        if sym == "BTCEUR":
            btceur_status = service.symbol_health.get("BTCEUR", {}).get("status", "OK")
            if btceur_status in ("ERROR", "DISABLED"):
                line += f" ⚠️ ({btceur_status})"
        lines.append(line)

        if not active:
            lines.append("  • Estado: Inactivo (no se evalúan señales)")
            lines.append("")
            continue

        if mt5_error is not None:
            lines.append(f"  • Error conectando a MT5: {mt5_error}")
            lines.append("")
            continue

        try:
            df = service.get_candles(sym, service.TIMEFRAME, service.CANDLES)
        except Exception as e:
            lines.append(f"  • Error obteniendo datos: {e}")
            lines.append("")
            continue

        try:
            cfg = service.RULES_CONFIG.get(sym.upper(), {}) or {}
            strat = cfg.get("strategy", "ema50_200")
            if sym == "BTCEUR" and "btceur" not in strat.lower():
                logger.error("[BTCEUR FIX] Strategy corregida automáticamente en /pairs: %s → btceur_simple", strat)
                strat = "btceur_simple"
            from signals import detect_signal, detect_signal_advanced
            basic_signal, _ = detect_signal(df, strategy=strat, config=cfg, symbol=sym)
            advanced_signal, _, adv_info = detect_signal_advanced(df, strategy=strat, config=cfg, current_balance=5000.0, symbol=sym)
        except Exception as e:
            lines.append(f"  • Error evaluando señal: {e}")
            lines.append("")
            continue

        try:
            last_price = float(df["close"].iloc[-1])
            if sym == "XAUUSD":
                price_str = f"{last_price:.2f}"
            elif sym == "BTCEUR":
                price_str = f"{last_price:.0f}"
            else:
                price_str = f"{last_price:.5f}"
        except Exception:
            price_str = "N/A"

        basic_ok = basic_signal is not None
        adv_ok = advanced_signal is not None
        confidence = "N/A"
        score = 0.0
        reason = None
        if isinstance(adv_info, dict):
            confidence = adv_info.get('confidence', 'N/A')
            score = float(adv_info.get('score', 0.0))
            reason = adv_info.get('rejection_reason') or adv_info.get('reason')

        lines.append(f"  • Precio: {price_str}")
        lines.append(f"  • Estrategia: {strat}")
        lines.append(f"  • Señal básica: {'✅' if basic_ok else '❌'}")
        lines.append(f"  • Señal avanzada: {'✅' if adv_ok else '❌'}")
        lines.append(f"  • Confianza: {confidence} | Score: {score:.2f}")
        if not adv_ok and reason:
            lines.append(f"  • Motivo rechazo: {str(reason)[:100]}")
        lines.append("")

    if mt5_error is not None:
        lines.append("⚠️ No se pudo conectar a MT5; solo se muestra el estado de activación de los pares.")

    return "\n".join(lines).strip()


def _get_period_status(service) -> dict:
    """Obtiene el estado actual del período."""
    from core import get_current_period_start
    from datetime import timedelta
    current_period_start = get_current_period_start()
    if current_period_start > service.state.current_period_start:
        old_count = service.state.trades_current_period
        service.state.trades_current_period = 0
        service.state.current_period_start = current_period_start
        period_name = "00:00-12:00" if service.state.current_period_start.hour == 0 else "12:00-24:00"
        service.log_event(f"🔄 NUEVO PERÍODO: {period_name} UTC | Trades resetados: {old_count} → 0", "INFO", "PERIOD")
    period_name = "00:00-12:00" if service.state.current_period_start.hour == 0 else "12:00-24:00"
    next_reset = service.state.current_period_start + timedelta(hours=12)
    time_until_reset = next_reset - datetime.now(timezone.utc)
    return {
        'current_period': period_name,
        'trades_current_period': service.state.trades_current_period,
        'max_trades_per_period': service.MAX_TRADES_PER_PERIOD,
        'trades_remaining': max(0, service.MAX_TRADES_PER_PERIOD - service.state.trades_current_period),
        'next_reset': next_reset,
        'time_until_reset': time_until_reset,
        'period_full': service.state.trades_current_period >= service.MAX_TRADES_PER_PERIOD
    }


def _reset_period_if_needed(service):
    """Resetea el contador de trades si estamos en un nuevo período."""
    from core import get_current_period_start
    current_period_start = get_current_period_start()
    if current_period_start > service.state.current_period_start:
        old_count = service.state.trades_current_period
        service.state.trades_current_period = 0
        service.state.current_period_start = current_period_start
        period_name = "00:00-12:00" if service.state.current_period_start.hour == 0 else "12:00-24:00"
        service.log_event(f"🔄 NUEVO PERÍODO: {period_name} UTC | Trades resetados: {old_count} → 0", "INFO", "PERIOD")


# ── Factory function ───────────────────────────────────────────────────────────

def create_commands_service(bot, state, config):
    """Factory para crear el servicio de comandos."""
    service = CommandsService(bot, state, config)
    # Inyectar funciones auxiliares
    service.compute_suggested_lot = lambda signal, risk_pct=None: _compute_suggested_lot(service, signal, risk_pct)
    service.build_pairs_overview_text = lambda: _build_pairs_overview_text(service)
    service.get_period_status = lambda: _get_period_status(service)
    service.reset_period_if_needed = lambda: _reset_period_if_needed(service)
    from services.database import save_trades_today
    service.save_trades_today = save_trades_today
    from services.logging import get_intelligent_logger
    service.bot_logger = get_intelligent_logger()
    return service
