"""
LastEdge Play Store Phone Screenshots Generator
Generates 5 institutional 1080x1920 (9:16) Play Store screenshots in official brand identity.
"""

import os
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUTPUT_DIRS = [
    Path(r"C:\LastEdge\branding\playstore\phone-screenshots"),
    Path(r"C:\LastEdge\LastEdge App\branding\playstore\phone-screenshots"),
]

FONTS_DIR = Path(r"C:\LastEdge\docs\assets\fonts")
NEXA_PATH = str(FONTS_DIR / "Nexa.ttf")
JAKARTA_BOLD = str(FONTS_DIR / "PlusJakartaSans-Bold.ttf")
JAKARTA_SEMI = str(FONTS_DIR / "PlusJakartaSans-SemiBold.ttf")
JAKARTA_REG = str(FONTS_DIR / "PlusJakartaSans-Regular.ttf")

LOGO_PATH = Path(r"C:\LastEdge\branding\LastEdge_Logo_Transparent.png")
CHART_PATH = Path(r"C:\LastEdge\LastEdge App\logs\charts\chart_EURUSD_20261110_101503_ec50d3.png")

# Brand Colors
BG_DARK = (7, 9, 14)          # #07090E
CARD_BG = (12, 16, 24)        # #0C1018
CARD_INNER = (17, 23, 34)     # #111722
CARD_BORDER = (26, 35, 51)    # #1A2333
TEXT_WHITE = (255, 255, 255)
TEXT_MAIN = (243, 244, 246)
TEXT_MUTED = (148, 163, 184)
TEXT_DIM = (100, 116, 139)
ACCENT_GREEN = (16, 185, 129) # #10B981
ACCENT_BLUE = (56, 189, 248)  # #38BDF8
ACCENT_RED = (244, 63, 94)    # #F43F5E
ACCENT_PURPLE = (167, 139, 250)

WIDTH, HEIGHT = 1080, 1920

def get_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def create_base_canvas(glow_color=(16, 185, 129, 30), glow_pos=(540, 150)):
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG_DARK + (255,))
    
    # Subtle radial glow
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    gx, gy = glow_pos
    max_r = 500
    for r in range(max_r, 0, -10):
        alpha = int((1 - (r / max_r) ** 2) * glow_color[3])
        color = glow_color[:3] + (alpha,)
        glow_draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=color)
    
    canvas = Image.alpha_composite(canvas, glow)
    return canvas

def draw_pill(draw, xy, text, font, bg_color, text_color, border_color=None):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) // 2, fill=bg_color, outline=border_color, width=1)
    # Center text
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x0 + (x1 - x0 - tw) / 2
    ty = y0 + (y1 - y0 - th) / 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill=text_color)

def draw_phone_frame(draw, x0=80, y0=420, x1=1000, y1=1920):
    # Outer bezel
    draw.rounded_rectangle([x0, y0, x1, y1], radius=54, fill=(18, 24, 38), outline=(38, 53, 77), width=3)
    # Inner display
    ix0, iy0, ix1, iy1 = x0 + 14, y0 + 14, x1 - 14, y1 - 2
    draw.rounded_rectangle([ix0, iy0, ix1, iy1], radius=44, fill=(8, 11, 16))
    
    # Dynamic Island / Notch
    notch_w = 170
    notch_h = 32
    nx0 = (ix0 + ix1 - notch_w) // 2
    ny0 = iy0 + 14
    draw.rounded_rectangle([nx0, ny0, nx0 + notch_w, ny0 + notch_h], radius=16, fill=(0, 0, 0))
    
    # Status bar icons
    font_status = get_font(JAKARTA_BOLD, 20)
    draw.text((ix0 + 36, iy0 + 20), "09:41", font=font_status, fill=TEXT_MUTED)
    draw.text((ix1 - 120, iy0 + 20), "5G  ● 100%", font=font_status, fill=TEXT_MUTED)
    
    return ix0, iy0, ix1, iy1

def draw_app_header(draw, ix0, iy0, ix1, logo_img, active_tab="OVERVIEW"):
    # App brand bar inside phone
    hy = iy0 + 64
    if logo_img:
        logo_thumb = logo_img.copy()
        logo_thumb.thumbnail((38, 38), Image.Resampling.LANCZOS)
        # paste logo
        draw.bitmap((ix0 + 32, hy), logo_thumb)
    
    font_brand = get_font(NEXA_PATH, 24)
    draw.text((ix0 + 78, hy + 4), "LASTEDGE", font=font_brand, fill=TEXT_WHITE)
    
    # Status indicator
    font_status = get_font(JAKARTA_SEMI, 16)
    draw_pill(draw, [ix1 - 230, hy + 2, ix1 - 32, hy + 36], "● MT5 ONLINE (12ms)", font_status, (16, 185, 129, 30), ACCENT_GREEN, (16, 185, 129, 80))

def draw_bottom_nav(draw, ix0, ix1, iy1, active_idx=0):
    nav_h = 80
    ny0 = iy1 - nav_h - 20
    draw.line([ix0, ny0, ix1, ny0], fill=CARD_BORDER, width=1)
    
    tabs = ["DASHBOARD", "TRADES", "STRATEGY LAB", "SETTINGS"]
    tab_w = (ix1 - ix0) / len(tabs)
    font_nav = get_font(JAKARTA_BOLD, 15)
    
    for i, tab in enumerate(tabs):
        tx = ix0 + i * tab_w + tab_w / 2
        color = ACCENT_GREEN if i == active_idx else TEXT_DIM
        bbox = font_nav.getbbox(tab)
        w = bbox[2] - bbox[0]
        draw.text((tx - w / 2, ny0 + 28), tab, font=font_nav, fill=color)

def generate_screenshot_1():
    """Screenshot 1: Institutional Portfolio & Telemetry"""
    img = create_base_canvas(glow_color=(16, 185, 129, 45), glow_pos=(540, 180))
    draw = ImageDraw.Draw(img)
    
    # Marketing Header
    draw_pill(draw, [380, 70, 700, 116], "INSTITUTIONAL TELEMETRY", get_font(JAKARTA_BOLD, 18), (16, 185, 129, 30), ACCENT_GREEN, (16, 185, 129, 90))
    
    font_title = get_font(NEXA_PATH, 48)
    draw.text((540, 150), "MONITOREO DE CARTERA", font=font_title, fill=TEXT_WHITE, anchor="mm")
    
    font_sub = get_font(JAKARTA_REG, 24)
    draw.text((540, 215), "Balance, exposición y telemetría de ejecución en MetaTrader 5", font=font_sub, fill=TEXT_MUTED, anchor="mm")
    
    # Phone Frame
    logo = Image.open(LOGO_PATH).convert("RGBA") if LOGO_PATH.exists() else None
    ix0, iy0, ix1, iy1 = draw_phone_frame(draw, y0=310)
    global ix1_g; ix1_g = ix1
    draw_app_header(draw, ix0, iy0, ix1, logo, "OVERVIEW")
    
    # Main Balance Card inside phone
    by0 = iy0 + 120
    by1 = by0 + 220
    draw.rounded_rectangle([ix0 + 28, by0, ix1 - 28, by1], radius=24, fill=CARD_BG, outline=CARD_BORDER, width=1)
    
    font_lbl = get_font(JAKARTA_SEMI, 17)
    draw.text((ix0 + 52, by0 + 26), "EQUITY TOTAL CONSOLIDADO", font=font_lbl, fill=TEXT_MUTED)
    
    font_big = get_font(NEXA_PATH, 54)
    draw.text((ix0 + 52, by0 + 64), "€ 124,580.45", font=font_big, fill=TEXT_WHITE)
    
    draw_pill(draw, [ix1 - 240, by0 + 72, ix1 - 52, by0 + 116], "▲ +€1,420.80 (+1.15%)", get_font(JAKARTA_BOLD, 15), (16, 185, 129, 35), ACCENT_GREEN)
    
    # Secondary stats row
    draw.line([ix0 + 52, by0 + 140, ix1 - 52, by0 + 140], fill=CARD_BORDER, width=1)
    font_substats = get_font(JAKARTA_REG, 17)
    font_subval = get_font(JAKARTA_BOLD, 18)
    
    draw.text((ix0 + 52, by0 + 155), "Balance Inicial", font=font_lbl, fill=TEXT_DIM)
    draw.text((ix0 + 52, by0 + 180), "€ 123,159.65", font=font_subval, fill=TEXT_MAIN)
    
    draw.text((ix0 + 330, by0 + 155), "Margen Libre", font=font_lbl, fill=TEXT_DIM)
    draw.text((ix0 + 330, by0 + 180), "€ 120,760.45", font=font_subval, fill=TEXT_MAIN)
    
    draw.text((ix0 + 600, by0 + 155), "Nivel de Margen", font=font_lbl, fill=TEXT_DIM)
    draw.text((ix0 + 600, by0 + 180), "3,260 %", font=font_subval, fill=ACCENT_GREEN)
    
    # Bento Row: Winrate + Active Positions
    rw0 = by1 + 20
    rw1 = rw0 + 150
    half_w = (ix1 - ix0 - 72) // 2
    
    # Left Bento: Performance
    draw.rounded_rectangle([ix0 + 28, rw0, ix0 + 28 + half_w, rw1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw.text((ix0 + 48, rw0 + 22), "WINRATE HISTÓRICO", font=font_lbl, fill=TEXT_MUTED)
    draw.text((ix0 + 48, rw0 + 55), "68.4 %", font=get_font(NEXA_PATH, 38), fill=ACCENT_GREEN)
    draw.text((ix0 + 48, rw0 + 110), "Profit Factor: 1.92 · 1,240 trades", font=get_font(JAKARTA_REG, 15), fill=TEXT_DIM)
    
    # Right Bento: Risk Shield
    draw.rounded_rectangle([ix1 - 28 - half_w, rw0, ix1 - 28, rw1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw.text((ix1 - 28 - half_w + 20, rw0 + 22), "ESTADO DEL RISK ENGINE", font=font_lbl, fill=TEXT_MUTED)
    draw.text((ix1 - 28 - half_w + 20, rw0 + 55), "PROTEGIDO", font=get_font(NEXA_PATH, 34), fill=ACCENT_BLUE)
    draw.text((ix1 - 28 - half_w + 20, rw0 + 110), "SpreadGuard activo (< 1.8 pips)", font=get_font(JAKARTA_REG, 15), fill=TEXT_DIM)
    
    # Live Trades Title
    ty0 = rw1 + 28
    draw.text((ix0 + 32, ty0), "POSICIONES EN MERCADO (2)", font=get_font(JAKARTA_BOLD, 20), fill=TEXT_WHITE)
    
    # Live Trade Card 1: EURUSD
    t1_y0 = ty0 + 36
    t1_y1 = t1_y0 + 175
    draw.rounded_rectangle([ix0 + 28, t1_y0, ix1 - 28, t1_y1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw_pill(draw, [ix0 + 48, t1_y0 + 20, ix0 + 120, t1_y0 + 52], "BUY", get_font(JAKARTA_BOLD, 15), (16, 185, 129, 35), ACCENT_GREEN)
    draw.text((ix0 + 135, t1_y0 + 22), "EURUSD", font=get_font(NEXA_PATH, 24), fill=TEXT_WHITE)
    draw.text((ix0 + 260, t1_y0 + 26), "0.17 Lots · Breakout Alpha v2", font=get_font(JAKARTA_REG, 16), fill=TEXT_DIM)
    draw.text((ix1 - 190, t1_y0 + 20), "+€ 275.40", font=get_font(NEXA_PATH, 26), fill=ACCENT_GREEN)
    
    draw.line([ix0 + 48, t1_y0 + 72, ix1 - 48, t1_y0 + 72], fill=CARD_BORDER, width=1)
    draw.text((ix0 + 48, t1_y0 + 90), "Entrada: 1.12288", font=font_lbl, fill=TEXT_MUTED)
    draw.text((ix0 + 280, t1_y0 + 90), "Actual: 1.12450 (+16.2 pips)", font=font_lbl, fill=ACCENT_GREEN)
    draw.text((ix0 + 48, t1_y0 + 125), "SL: 1.11950", font=font_lbl, fill=ACCENT_RED)
    draw.text((ix0 + 280, t1_y0 + 125), "TP: 1.12960", font=font_lbl, fill=ACCENT_GREEN)
    draw_pill(draw, [ix1 - 220, t1_y0 + 115, ix1 - 48, t1_y0 + 155], "Trailing SL Activo", get_font(JAKARTA_BOLD, 14), (56, 189, 248, 25), ACCENT_BLUE)
    
    # Live Trade Card 2: BTCEUR
    t2_y0 = t1_y1 + 16
    t2_y1 = t2_y0 + 175
    draw.rounded_rectangle([ix0 + 28, t2_y0, ix1 - 28, t2_y1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw_pill(draw, [ix0 + 48, t2_y0 + 20, ix0 + 120, t2_y0 + 52], "SELL", get_font(JAKARTA_BOLD, 15), (244, 63, 94, 35), ACCENT_RED)
    draw.text((ix0 + 135, t2_y0 + 22), "BTCEUR", font=get_font(NEXA_PATH, 24), fill=TEXT_WHITE)
    draw.text((ix0 + 260, t2_y0 + 26), "0.01 Lots · Momentum Filter", font=get_font(JAKARTA_REG, 16), fill=TEXT_DIM)
    draw.text((ix1 - 170, t2_y0 + 20), "+€ 53.00", font=get_font(NEXA_PATH, 26), fill=ACCENT_GREEN)
    
    draw.line([ix0 + 48, t2_y0 + 72, ix1 - 48, t2_y0 + 72], fill=CARD_BORDER, width=1)
    draw.text((ix0 + 48, t2_y0 + 90), "Entrada: 88,450.00", font=font_lbl, fill=TEXT_MUTED)
    draw.text((ix0 + 280, t2_y0 + 90), "Actual: 87,920.00 (+530 pts)", font=font_lbl, fill=ACCENT_GREEN)
    draw.text((ix0 + 48, t2_y0 + 125), "SL: 89,800.00", font=font_lbl, fill=ACCENT_RED)
    draw.text((ix0 + 280, t2_y0 + 125), "TP: 85,200.00", font=font_lbl, fill=ACCENT_GREEN)
    draw_pill(draw, [ix1 - 200, t2_y0 + 115, ix1 - 48, t2_y0 + 155], "En Beneficio", get_font(JAKARTA_BOLD, 14), (16, 185, 129, 25), ACCENT_GREEN)
    
    draw_bottom_nav(draw, ix0, ix1, iy1, active_idx=0)
    return img

def generate_screenshot_2():
    """Screenshot 2: Visual Chart & Automated Signals"""
    img = create_base_canvas(glow_color=(56, 189, 248, 45), glow_pos=(540, 180))
    draw = ImageDraw.Draw(img)
    
    # Marketing Header
    draw_pill(draw, [350, 70, 730, 116], "ALGORITHMIC VISUAL ENGINE", get_font(JAKARTA_BOLD, 18), (56, 189, 248, 30), ACCENT_BLUE, (56, 189, 248, 90))
    
    font_title = get_font(NEXA_PATH, 48)
    draw.text((540, 150), "SEÑALES Y EJECUCIÓN VISUAL", font=font_title, fill=TEXT_WHITE, anchor="mm")
    
    font_sub = get_font(JAKARTA_REG, 24)
    draw.text((540, 215), "Gráficos técnicos con proyección TP/SL y niveles institucionales", font=font_sub, fill=TEXT_MUTED, anchor="mm")
    
    # Phone Frame
    logo = Image.open(LOGO_PATH).convert("RGBA") if LOGO_PATH.exists() else None
    ix0, iy0, ix1, iy1 = draw_phone_frame(draw, y0=310)
    draw_app_header(draw, ix0, iy0, ix1, logo, "SIGNALS")
    
    # Trade Signal Banner
    sy0 = iy0 + 120
    sy1 = sy0 + 110
    draw.rounded_rectangle([ix0 + 28, sy0, ix1 - 28, sy1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    
    draw_pill(draw, [ix0 + 48, sy0 + 24, ix0 + 140, sy0 + 64], "BUY", get_font(JAKARTA_BOLD, 18), (16, 185, 129, 35), ACCENT_GREEN)
    draw.text((ix0 + 160, sy0 + 24), "EURUSD · M5", font=get_font(NEXA_PATH, 28), fill=TEXT_WHITE)
    draw.text((ix0 + 160, sy0 + 66), "Estrategia: Volatility Breakout Pro", font=get_font(JAKARTA_REG, 17), fill=TEXT_MUTED)
    
    draw_pill(draw, [ix1 - 230, sy0 + 32, ix1 - 50, sy0 + 78], "R:R 1 : 2.8", get_font(JAKARTA_BOLD, 18), (56, 189, 248, 25), ACCENT_BLUE)
    
    # Real Technical Chart Image
    cy0 = sy1 + 18
    chart_h = 520
    cy1 = cy0 + chart_h
    
    if CHART_PATH.exists():
        chart_raw = Image.open(CHART_PATH).convert("RGBA")
        cw = ix1 - ix0 - 56
        chart_resized = chart_raw.resize((cw, chart_h), Image.Resampling.LANCZOS)
        
        # Rounded mask for chart
        mask = Image.new("L", (cw, chart_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([0, 0, cw, chart_h], radius=20, fill=255)
        
        img.paste(chart_resized, (ix0 + 28, cy0), mask)
        draw.rounded_rectangle([ix0 + 28, cy0, ix1 - 28, cy1], radius=20, outline=CARD_BORDER, width=2)
    
    # Trade Execution Levels Card
    ly0 = cy1 + 20
    ly1 = ly0 + 240
    draw.rounded_rectangle([ix0 + 28, ly0, ix1 - 28, ly1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    
    draw.text((ix0 + 48, ly0 + 24), "PARÁMETROS DE EJECUCIÓN", font=get_font(JAKARTA_BOLD, 18), fill=TEXT_WHITE)
    
    # 3 columns: Entry, SL, TP
    col_w = (ix1 - ix0 - 96) // 3
    c1 = ix0 + 48
    c2 = c1 + col_w
    c3 = c2 + col_w
    
    font_clbl = get_font(JAKARTA_SEMI, 16)
    font_cval = get_font(NEXA_PATH, 26)
    
    draw.text((c1, ly0 + 70), "PRECIO ENTRADA", font=font_clbl, fill=TEXT_DIM)
    draw.text((c1, ly0 + 105), "1.12288", font=font_cval, fill=TEXT_WHITE)
    draw.text((c1, ly0 + 145), "Orden al mercado", font=get_font(JAKARTA_REG, 15), fill=TEXT_MUTED)
    
    draw.text((c2, ly0 + 70), "STOP LOSS", font=font_clbl, fill=TEXT_DIM)
    draw.text((c2, ly0 + 105), "1.11950", font=font_cval, fill=ACCENT_RED)
    draw.text((c2, ly0 + 145), "-33.8 pips (-0.8%)", font=get_font(JAKARTA_REG, 15), fill=ACCENT_RED)
    
    draw.text((c3, ly0 + 70), "TAKE PROFIT", font=font_clbl, fill=TEXT_DIM)
    draw.text((c3, ly0 + 105), "1.12960", font=font_cval, fill=ACCENT_GREEN)
    draw.text((c3, ly0 + 145), "+67.2 pips (+2.2%)", font=get_font(JAKARTA_REG, 15), fill=ACCENT_GREEN)
    
    # Action Button inside phone
    btn_y0 = ly1 + 18
    btn_y1 = btn_y0 + 75
    draw.rounded_rectangle([ix0 + 28, btn_y0, ix1 - 28, btn_y1], radius=18, fill=(16, 185, 129, 220))
    draw.text(((ix0 + ix1) // 2, (btn_y0 + btn_y1) // 2), "MODIFICAR TRAILING SL / REPLICAR", font=get_font(JAKARTA_BOLD, 18), fill=TEXT_WHITE, anchor="mm")
    
    draw_bottom_nav(draw, ix0, ix1, iy1, active_idx=1)
    return img

def generate_screenshot_3():
    """Screenshot 3: Strategy Lab & Quantitative Backtest"""
    img = create_base_canvas(glow_color=(167, 139, 250, 45), glow_pos=(540, 180))
    draw = ImageDraw.Draw(img)
    
    # Marketing Header
    draw_pill(draw, [340, 70, 740, 116], "QUANTITATIVE RESEARCH LAB", get_font(JAKARTA_BOLD, 18), (167, 139, 250, 30), ACCENT_PURPLE, (167, 139, 250, 90))
    
    font_title = get_font(NEXA_PATH, 48)
    draw.text((540, 150), "LABORATORIO Y BACKTESTING", font=font_title, fill=TEXT_WHITE, anchor="mm")
    
    font_sub = get_font(JAKARTA_REG, 24)
    draw.text((540, 215), "Validación algorítmica y curvas de rendimiento institucional", font=font_sub, fill=TEXT_MUTED, anchor="mm")
    
    # Phone Frame
    logo = Image.open(LOGO_PATH).convert("RGBA") if LOGO_PATH.exists() else None
    ix0, iy0, ix1, iy1 = draw_phone_frame(draw, y0=310)
    draw_app_header(draw, ix0, iy0, ix1, logo, "LAB")
    
    # Strategy Selector Card
    sy0 = iy0 + 120
    sy1 = sy0 + 110
    draw.rounded_rectangle([ix0 + 28, sy0, ix1 - 28, sy1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw.text((ix0 + 48, sy0 + 24), "ESTRATEGIA SELECCIONADA", font=get_font(JAKARTA_SEMI, 16), fill=TEXT_DIM)
    draw.text((ix0 + 48, sy0 + 56), "Trend Following Alpha v2.4", font=get_font(NEXA_PATH, 28), fill=TEXT_WHITE)
    draw_pill(draw, [ix1 - 200, sy0 + 32, ix1 - 48, sy0 + 78], "M15 / H1", get_font(JAKARTA_BOLD, 16), (167, 139, 250, 30), ACCENT_PURPLE)
    
    # Backtest Metrics Bento Grid
    by0 = sy1 + 18
    by1 = by0 + 260
    draw.rounded_rectangle([ix0 + 28, by0, ix1 - 28, by1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    
    draw.text((ix0 + 48, by0 + 24), "MÉTRICAS DEL BACKTESTING (10 AÑOS)", font=get_font(JAKARTA_BOLD, 18), fill=TEXT_WHITE)
    
    # 4 Key Metrics
    m_w = (ix1 - ix0 - 72) // 2
    
    # Retorno Total
    draw.text((ix0 + 48, by0 + 75), "Retorno Neto Acumulado", font=get_font(JAKARTA_REG, 16), fill=TEXT_DIM)
    draw.text((ix0 + 48, by0 + 105), "+ 142.8 %", font=get_font(NEXA_PATH, 34), fill=ACCENT_GREEN)
    
    # Sharpe Ratio
    draw.text((ix0 + 48 + m_w, by0 + 75), "Sharpe Ratio", font=get_font(JAKARTA_REG, 16), fill=TEXT_DIM)
    draw.text((ix0 + 48 + m_w, by0 + 105), "2.45", font=get_font(NEXA_PATH, 34), fill=ACCENT_BLUE)
    
    draw.line([ix0 + 48, by0 + 160, ix1 - 48, by0 + 160], fill=CARD_BORDER, width=1)
    
    # Max Drawdown
    draw.text((ix0 + 48, by0 + 180), "Max Drawdown Histórico", font=get_font(JAKARTA_REG, 16), fill=TEXT_DIM)
    draw.text((ix0 + 48, by0 + 210), "4.2 %", font=get_font(NEXA_PATH, 30), fill=TEXT_WHITE)
    
    # Calmar Ratio
    draw.text((ix0 + 48 + m_w, by0 + 180), "Profit Factor", font=get_font(JAKARTA_REG, 16), fill=TEXT_DIM)
    draw.text((ix0 + 48 + m_w, by0 + 210), "1.92", font=get_font(NEXA_PATH, 30), fill=ACCENT_GREEN)
    
    # Simulated Equity Curve Card
    cy0 = by1 + 18
    cy1 = cy0 + 360
    draw.rounded_rectangle([ix0 + 28, cy0, ix1 - 28, cy1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw.text((ix0 + 48, cy0 + 24), "CURVA DE CAPITAL HISTÓRICA (MONTE CARLO)", font=get_font(JAKARTA_BOLD, 18), fill=TEXT_WHITE)
    
    # Draw curve
    pts = []
    w_curve = ix1 - ix0 - 96
    h_curve = 230
    cx_base = ix0 + 48
    cy_base = cy0 + 75 + h_curve
    
    # Grid lines inside curve
    for gy in range(4):
        gl_y = cy_base - gy * (h_curve // 3)
        draw.line([cx_base, gl_y, cx_base + w_curve, gl_y], fill=(20, 27, 40), width=1)
    
    points_count = 60
    for i in range(points_count):
        px = cx_base + (i / (points_count - 1)) * w_curve
        # upward sloping trend with realistic volatility
        trend = (i / points_count) * (h_curve * 0.75)
        wave = math.sin(i * 0.4) * 15 + math.cos(i * 0.7) * 12
        py = cy_base - trend - wave - 20
        pts.append((px, py))
    
    # Draw glowing curve line
    draw.line(pts, fill=ACCENT_GREEN, width=4)
    # Highlight end point
    ex, ey = pts[-1]
    draw.ellipse([ex - 7, ey - 7, ex + 7, ey + 7], fill=ACCENT_GREEN, outline=TEXT_WHITE, width=2)
    draw.text((ex - 120, ey - 30), "€ 242,800 (+142%)", font=get_font(JAKARTA_BOLD, 16), fill=ACCENT_GREEN)
    
    draw_bottom_nav(draw, ix0, ix1, iy1, active_idx=2)
    return img

def generate_screenshot_4():
    """Screenshot 4: Institutional Risk Engine v2 & SpreadGuard"""
    img = create_base_canvas(glow_color=(244, 63, 94, 45), glow_pos=(540, 180))
    draw = ImageDraw.Draw(img)
    
    # Marketing Header
    draw_pill(draw, [350, 70, 730, 116], "CAPITAL PRESERVATION SYSTEM", get_font(JAKARTA_BOLD, 18), (244, 63, 94, 30), ACCENT_RED, (244, 63, 94, 90))
    
    font_title = get_font(NEXA_PATH, 48)
    draw.text((540, 150), "GESTIÓN DE RIESGO AVANZADA", font=font_title, fill=TEXT_WHITE, anchor="mm")
    
    font_sub = get_font(JAKARTA_REG, 24)
    draw.text((540, 215), "SpreadGuard dinámico, límites de Drawdown y Kill-Switch", font=font_sub, fill=TEXT_MUTED, anchor="mm")
    
    # Phone Frame
    logo = Image.open(LOGO_PATH).convert("RGBA") if LOGO_PATH.exists() else None
    ix0, iy0, ix1, iy1 = draw_phone_frame(draw, y0=310)
    draw_app_header(draw, ix0, iy0, ix1, logo, "SETTINGS")
    
    # Risk Guard Status Card
    ry0 = iy0 + 120
    ry1 = ry0 + 140
    draw.rounded_rectangle([ix0 + 28, ry0, ix1 - 28, ry1], radius=20, fill=CARD_BG, outline=(244, 63, 94, 100), width=1)
    
    draw_pill(draw, [ix0 + 48, ry0 + 24, ix0 + 180, ry0 + 64], "● ACTIVO", get_font(JAKARTA_BOLD, 16), (16, 185, 129, 30), ACCENT_GREEN)
    draw.text((ix0 + 200, ry0 + 26), "RISK ENGINE v2 OPERACIONAL", font=get_font(NEXA_PATH, 24), fill=TEXT_WHITE)
    draw.text((ix0 + 48, ry0 + 82), "Monitoreo de latencia, slippage y exposición global por activo", font=get_font(JAKARTA_REG, 17), fill=TEXT_MUTED)
    
    # Drawdown Gauges Bento
    gy0 = ry1 + 20
    gy1 = gy0 + 280
    draw.rounded_rectangle([ix0 + 28, gy0, ix1 - 28, gy1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw.text((ix0 + 48, gy0 + 24), "CONTROL DE DRAWDOWN DIARIO Y TOTAL", font=get_font(JAKARTA_BOLD, 18), fill=TEXT_WHITE)
    
    # Progress bar 1: Daily DD
    draw.text((ix0 + 48, gy0 + 72), "Drawdown Diario Actual", font=get_font(JAKARTA_SEMI, 16), fill=TEXT_DIM)
    draw.text((ix1 - 220, gy0 + 72), "1.15 % / 3.00 %", font=get_font(JAKARTA_BOLD, 16), fill=ACCENT_GREEN)
    # bar background
    bar_w = ix1 - ix0 - 96
    draw.rounded_rectangle([ix0 + 48, gy0 + 105, ix0 + 48 + bar_w, gy0 + 125], radius=10, fill=CARD_INNER)
    draw.rounded_rectangle([ix0 + 48, gy0 + 105, ix0 + 48 + int(bar_w * 0.38), gy0 + 125], radius=10, fill=ACCENT_GREEN)
    
    # Progress bar 2: Max Total DD
    draw.text((ix0 + 48, gy0 + 155), "Drawdown Máximo Histórico", font=get_font(JAKARTA_SEMI, 16), fill=TEXT_DIM)
    draw.text((ix1 - 220, gy0 + 155), "4.80 % / 10.00 %", font=get_font(JAKARTA_BOLD, 16), fill=ACCENT_BLUE)
    draw.rounded_rectangle([ix0 + 48, gy0 + 188, ix0 + 48 + bar_w, gy0 + 208], radius=10, fill=CARD_INNER)
    draw.rounded_rectangle([ix0 + 48, gy0 + 188, ix0 + 48 + int(bar_w * 0.48), gy0 + 208], radius=10, fill=ACCENT_BLUE)
    
    draw.text((ix0 + 48, gy0 + 235), "SpreadGuard: 0.8 pips (Umbral máx: 1.8 pips) · OK", font=get_font(JAKARTA_REG, 15), fill=TEXT_MUTED)
    
    # Asset Allocation Row
    ay0 = gy1 + 20
    ay1 = ay0 + 180
    draw.rounded_rectangle([ix0 + 28, ay0, ix1 - 28, ay1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw.text((ix0 + 48, ay0 + 24), "EXPOSICIÓN POR CLASE DE ACTIVO", font=get_font(JAKARTA_BOLD, 18), fill=TEXT_WHITE)
    
    col3 = (ix1 - ix0 - 96) // 3
    draw.text((ix0 + 48, ay0 + 75), "Forex Majors", font=get_font(JAKARTA_REG, 16), fill=TEXT_DIM)
    draw.text((ix0 + 48, ay0 + 105), "45.0 %", font=get_font(NEXA_PATH, 28), fill=ACCENT_GREEN)
    
    draw.text((ix0 + 48 + col3, ay0 + 75), "Commodities", font=get_font(JAKARTA_REG, 16), fill=TEXT_DIM)
    draw.text((ix0 + 48 + col3, ay0 + 105), "35.0 %", font=get_font(NEXA_PATH, 28), fill=ACCENT_BLUE)
    
    draw.text((ix0 + 48 + col3 * 2, ay0 + 75), "Crypto", font=get_font(JAKARTA_REG, 16), fill=TEXT_DIM)
    draw.text((ix0 + 48 + col3 * 2, ay0 + 105), "20.0 %", font=get_font(NEXA_PATH, 28), fill=ACCENT_PURPLE)
    
    # Emergency Kill Switch Card
    ky0 = ay1 + 20
    ky1 = ky0 + 120
    draw.rounded_rectangle([ix0 + 28, ky0, ix1 - 28, ky1], radius=20, fill=(244, 63, 94, 25), outline=ACCENT_RED, width=1)
    draw.text((ix0 + 48, ky0 + 26), "KILL-SWITCH DE EMERGENCIA", font=get_font(NEXA_PATH, 22), fill=ACCENT_RED)
    draw.text((ix0 + 48, ky0 + 64), "Cierre forzado instantáneo de todas las posiciones en MT5", font=get_font(JAKARTA_REG, 15), fill=TEXT_MUTED)
    draw_pill(draw, [ix1 - 180, ky0 + 35, ix1 - 48, ky0 + 85], "ARMADO", get_font(JAKARTA_BOLD, 16), (244, 63, 94, 40), ACCENT_RED)
    
    draw_bottom_nav(draw, ix0, ix1, iy1, active_idx=3)
    return img

def generate_screenshot_5():
    """Screenshot 5: Instant Signals & Multi-Terminal Dispatch"""
    img = create_base_canvas(glow_color=(16, 185, 129, 45), glow_pos=(540, 180))
    draw = ImageDraw.Draw(img)
    
    # Marketing Header
    draw_pill(draw, [340, 70, 740, 116], "DUAL REAL-TIME REPLICATION", get_font(JAKARTA_BOLD, 18), (16, 185, 129, 30), ACCENT_GREEN, (16, 185, 129, 90))
    
    font_title = get_font(NEXA_PATH, 48)
    draw.text((540, 150), "REPLICACIÓN Y ALERTAS VIP", font=font_title, fill=TEXT_WHITE, anchor="mm")
    
    font_sub = get_font(JAKARTA_REG, 24)
    draw.text((540, 215), "Despacho instantáneo a canales VIP con gráficos e informes", font=font_sub, fill=TEXT_MUTED, anchor="mm")
    
    # Phone Frame
    logo = Image.open(LOGO_PATH).convert("RGBA") if LOGO_PATH.exists() else None
    ix0, iy0, ix1, iy1 = draw_phone_frame(draw, y0=310)
    draw_app_header(draw, ix0, iy0, ix1, logo, "DISPATCH")
    
    # Channels Connectivity Card
    cy0 = iy0 + 120
    cy1 = cy0 + 175
    draw.rounded_rectangle([ix0 + 28, cy0, ix1 - 28, cy1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw.text((ix0 + 48, cy0 + 24), "CANALES DE REPLICACIÓN CONECTADOS", font=get_font(JAKARTA_BOLD, 18), fill=TEXT_WHITE)
    
    # Status item 1
    draw.ellipse([ix0 + 48, cy0 + 72, ix0 + 64, cy0 + 88], fill=ACCENT_GREEN)
    draw.text((ix0 + 78, cy0 + 68), "Terminal Principal MetaTrader 5 (Low Latency 12ms)", font=get_font(JAKARTA_REG, 16), fill=TEXT_MAIN)
    
    # Status item 2
    draw.ellipse([ix0 + 48, cy0 + 108, ix0 + 64, cy0 + 124], fill=ACCENT_GREEN)
    draw.text((ix0 + 78, cy0 + 104), "Canal VIP LastEdge Signals (Telegram Adapter)", font=get_font(JAKARTA_REG, 16), fill=TEXT_MAIN)
    
    # Status item 3
    draw.ellipse([ix0 + 48, cy0 + 144, ix0 + 64, cy0 + 160], fill=ACCENT_GREEN)
    draw.text((ix0 + 78, cy0 + 140), "Bot Privado de Supervisión y Comandos (/status, /close)", font=get_font(JAKARTA_REG, 16), fill=TEXT_MAIN)
    
    # Feed of Recent Dispatched Signals
    fy0 = cy1 + 20
    draw.text((ix0 + 32, fy0), "REGISTRO DE SEÑALES DESPACHADAS", font=get_font(JAKARTA_BOLD, 20), fill=TEXT_WHITE)
    
    # Alert Card 1
    a1_y0 = fy0 + 36
    a1_y1 = a1_y0 + 140
    draw.rounded_rectangle([ix0 + 28, a1_y0, ix1 - 28, a1_y1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw_pill(draw, [ix0 + 48, a1_y0 + 20, ix0 + 150, a1_y0 + 54], "ENVIADO", get_font(JAKARTA_BOLD, 14), (16, 185, 129, 30), ACCENT_GREEN)
    draw.text((ix0 + 165, a1_y0 + 22), "EURUSD BUY @ 1.12288", font=get_font(NEXA_PATH, 22), fill=TEXT_WHITE)
    draw.text((ix1 - 150, a1_y0 + 24), "10:15:03", font=get_font(JAKARTA_SEMI, 16), fill=TEXT_DIM)
    draw.text((ix0 + 48, a1_y0 + 75), "Gráfico técnico con caja de proyección TP/SL despachado al canal VIP.", font=get_font(JAKARTA_REG, 15), fill=TEXT_MUTED)
    draw.text((ix0 + 48, a1_y0 + 102), "Latencia de despacho: 34 ms · Confirmación de entrega OK", font=get_font(JAKARTA_REG, 14), fill=ACCENT_GREEN)
    
    # Alert Card 2
    a2_y0 = a1_y1 + 16
    a2_y1 = a2_y0 + 140
    draw.rounded_rectangle([ix0 + 28, a2_y0, ix1 - 28, a2_y1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw_pill(draw, [ix0 + 48, a2_y0 + 20, ix0 + 150, a2_y0 + 54], "ENVIADO", get_font(JAKARTA_BOLD, 14), (16, 185, 129, 30), ACCENT_GREEN)
    draw.text((ix0 + 165, a2_y0 + 22), "BTCEUR SELL @ 88,450", font=get_font(NEXA_PATH, 22), fill=TEXT_WHITE)
    draw.text((ix1 - 150, a2_y0 + 24), "09:25:08", font=get_font(JAKARTA_SEMI, 16), fill=TEXT_DIM)
    draw.text((ix0 + 48, a2_y0 + 75), "Señal cuantitativa ejecutada en cuenta MT5 primaria y replicada.", font=get_font(JAKARTA_REG, 15), fill=TEXT_MUTED)
    draw.text((ix0 + 48, a2_y0 + 102), "Latencia de despacho: 28 ms · Confirmación de entrega OK", font=get_font(JAKARTA_REG, 14), fill=ACCENT_GREEN)
    
    # Alert Card 3
    a3_y0 = a2_y1 + 16
    a3_y1 = a3_y0 + 140
    draw.rounded_rectangle([ix0 + 28, a3_y0, ix1 - 28, a3_y1], radius=20, fill=CARD_BG, outline=CARD_BORDER, width=1)
    draw_pill(draw, [ix0 + 48, a3_y0 + 20, ix0 + 175, a3_y0 + 54], "AUDITORÍA", get_font(JAKARTA_BOLD, 14), (56, 189, 248, 30), ACCENT_BLUE)
    draw.text((ix0 + 190, a3_y0 + 22), "INFORME DIARIO GENERADO", font=get_font(NEXA_PATH, 22), fill=TEXT_WHITE)
    draw.text((ix1 - 150, a3_y0 + 24), "08:00:00", font=get_font(JAKARTA_SEMI, 16), fill=TEXT_DIM)
    draw.text((ix0 + 48, a3_y0 + 75), "Resumen analítico con métricas de Sharpe, Winrate y Drawdown.", font=get_font(JAKARTA_REG, 15), fill=TEXT_MUTED)
    draw.text((ix0 + 48, a3_y0 + 102), "Despachado a canal privado de administración", font=get_font(JAKARTA_REG, 14), fill=ACCENT_BLUE)
    
    draw_bottom_nav(draw, ix0, ix1, iy1, active_idx=1)
    return img

def main():
    for d in OUTPUT_DIRS:
        d.mkdir(parents=True, exist_ok=True)
        
    print("Generating screenshot 1: Dashboard...")
    s1 = generate_screenshot_1()
    
    print("Generating screenshot 2: Visual Chart & Signals...")
    s2 = generate_screenshot_2()
    
    print("Generating screenshot 3: Strategy Lab...")
    s3 = generate_screenshot_3()
    
    print("Generating screenshot 4: Risk Engine v2...")
    s4 = generate_screenshot_4()
    
    print("Generating screenshot 5: Replication & Alerts...")
    s5 = generate_screenshot_5()
    
    screens = [
        ("01_dashboard_telemetry.png", s1),
        ("02_visual_execution_chart.png", s2),
        ("03_strategy_lab_backtest.png", s3),
        ("04_risk_engine_spreadguard.png", s4),
        ("05_dual_replication_signals.png", s5),
    ]
    
    for filename, img in screens:
        for out_dir in OUTPUT_DIRS:
            dest = out_dir / filename
            img.save(dest, "PNG", optimize=True)
            print(f"Saved: {dest} ({img.size[0]}x{img.size[1]})")

if __name__ == "__main__":
    main()
