"""
Servicio de Comandos Discord — Refactored (Adaptador P2.1, P2.2 & P2.4)
=======================================================================
Adaptador limpio de comandos Discord Slash alineado con la arquitectura LastEdge.
Consume exclusivamente `BotService` como única capa de lógica de negocio.

Comandos Núcleo:
  /status          - Estado unificado del bot, uptime, MT5, Circuit Breaker y noticias
  /positions       - Posiciones abiertas en MT5 con P&L flotante en vivo
  /close_position  - Cierra una posición por número de ticket
  /equity          - Balance, equity, margen y nivel de margen
  /risk            - Telemetría de Risk Engine v2 y Circuit Breaker
  /journal         - Métricas de calidad de ejecución (30 días)
  /research        - Ficha de la Research Database e investigaciones
  /autosignals     - Estado y control de auto-ejecución (on/off/status)

Comandos Técnicos de Infraestructura:
  /health          - Diagnóstico técnico (MT5, DBs, Dashboard, APIs, CPU, RAM)
  /version         - Información de despliegue (Versión 1.1.0, Git Commit, Branch, Python)
  /logs            - Últimos eventos o errores importantes registrados
  /discord         - Metadata de registro técnico de Discord (App ID, Guild ID, Invite)
"""

import os
import logging
from typing import Optional
import discord
from discord.ext import commands

from services.bot_service import get_bot_service, BotService

logger = logging.getLogger(__name__)


class CommandsService:
    """Adaptador de Comandos Discord refactorizado y unificado."""

    def __init__(self, bot: commands.Bot, state, config: dict):
        self.bot = bot
        self.state = state
        self.config = config
        self.AUTHORIZED_USER_ID = config.get('AUTHORIZED_USER_ID', 0)
        self.bot_service: BotService = get_bot_service()

    def setup_commands(self):
        """Registra todos los Slash Commands en el árbol de comandos de Discord."""
        self._setup_slash_commands()

    def _setup_slash_commands(self):
        bot = self.bot

        # ── 1. /status ────────────────────────────────────────────────────────
        @bot.tree.command(name="status", description="Estado unificado del bot, uptime, MT5, Circuit Breaker y noticias.")
        async def slash_status(interaction: discord.Interaction):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            st = self.bot_service.get_system_status()
            mt5_st = "🟢 Conectado" if st["mt5_connected"] else "🔴 Desconectado"
            cb = st["circuit_breaker"]
            cb_st = "🟢 Activo" if cb.get("can_trade", True) else "🔴 Pausado"

            embed = discord.Embed(
                title="⚡ LastEdge — Estado General del Sistema",
                color=0x3b82f6 if st["mt5_connected"] else 0xef4444
            )
            embed.add_field(name="Estado Bot", value=f"`{st['system_status']}`", inline=True)
            embed.add_field(name="Uptime", value=f"`{st['uptime_formatted']}`", inline=True)
            embed.add_field(name="MT5 Broker", value=mt5_st, inline=True)
            embed.add_field(name="Cuenta MT5", value=f"`{st['account_number'] or '—'}`", inline=True)
            embed.add_field(name="Circuit Breaker", value=f"{cb_st} (×{cb.get('risk_multiplier', 1.0):.1f})", inline=True)
            embed.add_field(name="Autosignals", value="✅ Activo" if st["autosignals_enabled"] else "⏸ Desactivado", inline=True)
            
            pairs_str = ", ".join(st.get("monitored_symbols", []))
            embed.add_field(name="Pares Monitoreados", value=f"`{pairs_str}` ({st.get('scan_interval_seconds')}s)", inline=False)
            embed.add_field(name="Filtro de Noticias", value=st.get("news_indicator", "🟢 OK"), inline=False)
            
            embed.set_footer(text=f"Servidor Broker: {st.get('server') or 'n/a'}")
            await interaction.response.send_message(embed=embed)

        # ── 2. /positions ─────────────────────────────────────────────────────
        @bot.tree.command(name="positions", description="Posiciones abiertas en tiempo real en MetaTrader 5.")
        async def slash_positions(interaction: discord.Interaction):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            positions = self.bot_service.get_open_positions()
            if not positions:
                await interaction.response.send_message("ℹ️ No hay posiciones abiertas actualmente en MT5.", ephemeral=True)
                return

            embed = discord.Embed(title=f"📊 Posiciones Abiertas en MT5 ({len(positions)})", color=0x10b981)
            for p in positions:
                pnl_emoji = "🟢" if p["profit"] >= 0 else "🔴"
                val_str = (
                    f"Lotes: `{p['volume']:.2f}` | Entrada: `{p['open_price']:.5f}` | Actual: `{p['current_price']:.5f}`\n"
                    f"P&L: {pnl_emoji} **{p['profit']:+.2f} €** | SL: `{p['sl'] or '—'}` | TP: `{p['tp'] or '—'}`"
                )
                embed.add_field(name=f"#{p['ticket']} — {p['symbol']} ({p['type']})", value=val_str, inline=False)

            await interaction.response.send_message(embed=embed)

        # ── 3. /close_position ────────────────────────────────────────────────
        @bot.tree.command(name="close_position", description="Cierra una posición abierta especificando su número de Ticket.")
        @discord.app_commands.describe(ticket="Número de ticket de la posición a cerrar")
        async def slash_close_position(interaction: discord.Interaction, ticket: int):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            await interaction.response.defer(thinking=True)
            res = self.bot_service.close_position(ticket)
            msg = f"✅ {res['message']}" if res["ok"] else f"❌ {res['message']}"
            await interaction.followup.send(msg)

        # ── 4. /equity ────────────────────────────────────────────────────────
        @bot.tree.command(name="equity", description="Balance, equity, margen y métricas de la cuenta MT5.")
        async def slash_equity(interaction: discord.Interaction):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            acc = self.bot_service.get_account_equity()
            if not acc.get("ok"):
                await interaction.response.send_message(f"❌ Error: {acc.get('message')}", ephemeral=True)
                return

            pnl = acc["floating_pnl"]
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"

            embed = discord.Embed(title="💰 Balance & Equity — MT5 Account", color=0x3b82f6)
            embed.add_field(name="Balance Base", value=f"**{acc['balance']:,.2f} {acc['currency']}**", inline=True)
            embed.add_field(name="Equity Actual", value=f"**{acc['equity']:,.2f} {acc['currency']}**", inline=True)
            embed.add_field(name="P&L Flotante", value=f"{pnl_emoji} **{pnl:+.2f} {acc['currency']}**", inline=True)
            embed.add_field(name="Margen Usado", value=f"`{acc['margin']:,.2f} {acc['currency']}`", inline=True)
            embed.add_field(name="Margen Libre", value=f"`{acc['free_margin']:,.2f} {acc['currency']}`", inline=True)
            embed.add_field(name="Nivel de Margen", value=f"`{acc['margin_level']:.1f}%`", inline=True)
            embed.set_footer(text=f"Cuenta: {acc['account']} | Apalancamiento: 1:{acc.get('leverage', 'N/A')}")

            await interaction.response.send_message(embed=embed)

        # ── 5. /risk ──────────────────────────────────────────────────────────
        @bot.tree.command(name="risk", description="Telemetría de Risk Engine v2 y estado del Circuit Breaker.")
        async def slash_risk(interaction: discord.Interaction):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            rk = self.bot_service.get_risk_telemetry()
            cb = rk["circuit_breaker"]
            status_str = "🟢 OPERATIVO" if rk["can_trade"] else "🔴 PAUSADO (Circuit Breaker)"

            embed = discord.Embed(title="🛡️ Risk Engine v2 — Telemetría de Riesgo", color=0xf59e0b if not rk["can_trade"] else 0x10b981)
            embed.add_field(name="Estado de Trading", value=f"**{status_str}**", inline=False)
            embed.add_field(name="Multiplicador de Riesgo", value=f"`×{cb.get('risk_multiplier', 1.0):.1f}`", inline=True)
            embed.add_field(name="Rachas", value=f"Perdidas: `{cb.get('consecutive_losses', 0)}` | Ganadas: `{cb.get('consecutive_wins', 0)}`", inline=True)
            embed.add_field(name="Posiciones Abiertas", value=f"`{rk['open_positions_count']}` ({rk['total_exposure_lots']} lotes total)", inline=True)
            embed.add_field(name="P&L Flotante Total", value=f"**{rk['total_floating_pnl']:+.2f} €**", inline=True)
            embed.add_field(name="Nivel de Margen", value=f"`{rk['margin_level_pct']:.1f}%`", inline=True)

            if not rk["can_trade"] and cb.get("reason"):
                embed.add_field(name="Motivo Pausa", value=f"⚠️ {cb['reason']}", inline=False)

            await interaction.response.send_message(embed=embed)

        # ── 6. /journal ───────────────────────────────────────────────────────
        @bot.tree.command(name="journal", description="Métricas de Calidad de Ejecución y Diario de Trading (30 días).")
        @discord.app_commands.describe(days="Días de historial a evaluar (por defecto: 30)")
        async def slash_journal(interaction: discord.Interaction, days: int = 30):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            res = self.bot_service.get_journal_summary(days=days)
            stats = res.get("stats", {})
            tot = stats.get("total_orders", 0)

            embed = discord.Embed(title=f"📖 Diario de Ejecución ({days} Días)", color=0x8b5cf6)
            embed.add_field(name="Total Órdenes", value=f"`{tot}`", inline=True)
            embed.add_field(name="Tasa de Rechazo", value=f"`{stats.get('rejection_rate_pct', 0.0):.1f}%`", inline=True)
            embed.add_field(name="Spread Medio", value=f"`{stats.get('avg_spread_pips', 0.0):.1f} pips`", inline=True)
            embed.add_field(name="Latencia Media", value=f"`{stats.get('avg_latency_ms', 0.0):.0f} ms`", inline=True)
            embed.add_field(name="Slippage Medio", value=f"`{stats.get('avg_slippage_pips', 0.0):+.2f} pips`", inline=True)
            embed.add_field(name="Costo Slippage", value=f"`{stats.get('total_slippage_cost_eur', 0.0):+.2f} €`", inline=True)

            await interaction.response.send_message(embed=embed)

        # ── 7. /research ──────────────────────────────────────────────────────
        @bot.tree.command(name="research", description="Resumen de la Research Database y estado de experimentos.")
        async def slash_research(interaction: discord.Interaction):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            res = self.bot_service.get_research_summary()
            embed = discord.Embed(title="🔬 Research Database — Resumen", color=0x06b6d4)
            embed.add_field(name="Total Experimentos", value=f"`{res['total_experiments']}`", inline=True)
            embed.add_field(name="Promocionados", value=f"`{res['promoted_count']}` (PROMOTED)", inline=True)
            embed.add_field(name="Candidatos", value=f"`{res['candidates_count']}` (CANDIDATE)", inline=True)

            recent = res.get("recent_experiments", [])
            if recent:
                items_str = ""
                for exp in recent[:3]:
                    st = exp.get("decision_status", "DRAFT")
                    pf = exp.get("best_profit_factor")
                    pf_str = f"PF: {pf:.2f}" if pf else "PF: —"
                    items_str += f"• **{exp.get('title')}** ({exp.get('symbol')}) — `{st}` | {pf_str}\n"
                embed.add_field(name="Experimentos Recientes", value=items_str, inline=False)

            await interaction.response.send_message(embed=embed)

        # ── 8. /autosignals ───────────────────────────────────────────────────
        @bot.tree.command(name="autosignals", description="Activa, desactiva o consulta la generación automática de señales.")
        @discord.app_commands.describe(mode="on, off o status")
        async def slash_autosignals(interaction: discord.Interaction, mode: str = "status"):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            res = self.bot_service.toggle_autosignals(mode)
            st_text = "✅ **ACTIVADA**" if res["autosignals_enabled"] else "⏸ **DESACTIVADA**"
            await interaction.response.send_message(f"⚡ Generación automática de señales: {st_text}", ephemeral=True)

        # ── 9. /health ────────────────────────────────────────────────────────
        @bot.tree.command(name="health", description="Diagnóstico técnico de salud e infraestructura de la plataforma.")
        async def slash_health(interaction: discord.Interaction):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            h = self.bot_service.get_health_status()
            embed = discord.Embed(title="🩺 LastEdge — Diagnóstico de Salud Técnica", color=0x10b981)
            embed.add_field(name="MT5 Broker", value=f"`{h['mt5']['status']}`", inline=True)
            embed.add_field(name="SQLite DB", value=f"`{h['sqlite']['status']}` ({h['sqlite']['size_kb']} KB)", inline=True)
            embed.add_field(name="Research DB", value=f"`{h['research_db']['status']}` ({h['research_db']['experiments']} exp)", inline=True)
            embed.add_field(name="Web Dashboard", value=f"`{h['dashboard']['status']}` (Puerto {h['dashboard']['port']})", inline=True)
            embed.add_field(name="Mobile REST API", value=f"`{h['mobile_api']['status']}` (Puerto {h['mobile_api']['port']})", inline=True)
            embed.add_field(name="Dispatcher", value=f"`{h['notification_dispatcher']['status']}`", inline=True)
            
            res_str = f"CPU: `{h['resources']['cpu_percent']}%` | RAM: `{h['resources']['ram_percent']}%` ({h['resources']['ram_used_mb']} MB)"
            embed.add_field(name="Recursos del Servidor", value=res_str, inline=False)
            await interaction.response.send_message(embed=embed)

        # ── 10. /version ──────────────────────────────────────────────────────
        @bot.tree.command(name="version", description="Información de la versión desplegada, commit de Git y build.")
        async def slash_version(interaction: discord.Interaction):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            v = self.bot_service.get_version_info()
            embed = discord.Embed(title="📦 LastEdge — Información de Despliegue", color=0x6366f1)
            embed.add_field(name="Plataforma", value=f"**{v['platform_name']}**", inline=False)
            embed.add_field(name="Versión", value=f"`v{v['version']}`", inline=True)
            embed.add_field(name="Git Commit", value=f"`{v['git_commit']}` (`{v['git_branch']}`)", inline=True)
            embed.add_field(name="Entorno", value=f"`{v['environment']}`", inline=True)
            embed.add_field(name="Python", value=f"`v{v['python_version']}`", inline=True)
            embed.add_field(name="Esquema DB", value=f"`{v['db_schema_version']}`", inline=True)
            embed.set_footer(text=f"Fecha de Build: {v['build_date']}")
            await interaction.response.send_message(embed=embed)

        # ── 11. /logs ─────────────────────────────────────────────────────────
        @bot.tree.command(name="logs", description="Muestra los eventos e incidentes recientes del sistema.")
        async def slash_logs(interaction: discord.Interaction):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            logs = self.bot_service.get_recent_logs(count=8)
            if not logs:
                await interaction.response.send_message("ℹ️ No hay registros recientes.", ephemeral=True)
                return

            embed = discord.Embed(title="📋 Registros Recientes del Sistema", color=0x64748b)
            text = ""
            for entry in logs:
                lvl = entry.get("level", "INFO")
                emoji = "🔴" if lvl == "ERROR" else ("⚠️" if lvl == "WARNING" else "🔹")
                text += f"{emoji} `[{entry.get('component')}]` {entry.get('message')}\n"
            
            embed.description = text[:4000]
            await interaction.response.send_message(embed=embed)

        # ── 12. /discord ──────────────────────────────────────────────────────
        @bot.tree.command(name="discord", description="Metadata técnica de registro y sincronización del bot en Discord.")
        async def slash_discord(interaction: discord.Interaction):
            if self.AUTHORIZED_USER_ID and interaction.user.id != self.AUTHORIZED_USER_ID:
                await interaction.response.send_message("⛔ No autorizado", ephemeral=True)
                return

            app_id = self.bot.application_id or (self.bot.user.id if self.bot.user else "—")
            guild_id = self.config.get("GUILD_ID", "Global")
            invite_url = f"https://discord.com/oauth2/authorize?client_id={app_id}&scope=bot%20applications.commands&permissions=8"
            
            cmd_count = len(self.bot.tree.get_commands())

            embed = discord.Embed(title="🤖 Metadata Técnica de Discord", color=0x5865f2)
            embed.add_field(name="Bot Tag", value=f"`{self.bot.user}`", inline=True)
            embed.add_field(name="Application ID", value=f"`{app_id}`", inline=True)
            embed.add_field(name="Guild ID", value=f"`{guild_id}`", inline=True)
            embed.add_field(name="Comandos Registrados", value=f"`{cmd_count}` comandos slash", inline=True)
            embed.add_field(name="URL de Invitación", value=f"[Autorizar Bot]({invite_url})", inline=False)
            embed.set_footer(text=f"Latencia WebSocket: {int(self.bot.latency * 1000)} ms")

            await interaction.response.send_message(embed=embed)


def create_commands_service(bot: commands.Bot, state, config: dict) -> CommandsService:
    svc = CommandsService(bot, state, config)
    svc.setup_commands()
    return svc
