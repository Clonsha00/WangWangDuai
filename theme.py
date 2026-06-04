"""
theme.py
--------
全域設計 Token。所有顏色、字型、間距集中在這裡，
其他模組只 import 這裡的常數，不自行 hardcode 顏色。
"""

import flet as ft

# ── 色彩系統 ──────────────────────────────────────────
BG_DARK      = "#0F1117"   # 最底層背景
BG_PANEL     = "#161B27"   # Sidebar / Card 背景
BG_SURFACE   = "#1E2535"   # 輸入框 / 列表項背景
BG_HOVER     = "#252D3D"   # Hover 態

ACCENT       = "#5B8DEF"   # 主強調色（柔藍）
ACCENT_SOFT  = "#1E3A6E"   # 強調色低飽和版（Chip 選中背景）
SUCCESS      = "#4ADE80"   # 收入 / 正值
DANGER       = "#F87171"   # 支出 / 警示
WARNING      = "#FBBF24"   # 注意

TEXT_PRIMARY  = "#E8EAED"  # 主文字
TEXT_SECONDARY = "#8B95A5" # 次要文字 / 說明
TEXT_DISABLED  = "#3D4557" # 停用 / 分隔線

# ── 字型 ──────────────────────────────────────────────
FONT_FAMILY = "Segoe UI"   # Windows 系統字，無需額外載入

# ── 間距 ──────────────────────────────────────────────
PAD_XS =  4
PAD_SM =  8
PAD_MD = 16
PAD_LG = 24
PAD_XL = 32

# ── Sidebar ───────────────────────────────────────────
SIDEBAR_WIDTH = 220

# ── 圓角 ──────────────────────────────────────────────
RADIUS_SM =  6
RADIUS_MD = 10
RADIUS_LG = 16

# ── 字型大小 Token ────────────────────────────────────
FONT_XS = 10
FONT_SM = 12
FONT_MD = 13
FONT_LG = 16
FONT_XL = 20

# ── 圖示大小 Token ────────────────────────────────────
ICON_XS = 12
ICON_SM = 14
ICON_MD = 18

# ── 標籤調色盤 ────────────────────────────────────────
TAG_PALETTE = ["#E74C3C", "#E67E22", "#F1C40F", "#2ECC71", "#3498DB", "#9B59B6", "#34495E", "#95A5A6"]

# ── Flet Theme 物件 ───────────────────────────────────

def build_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=ACCENT,
        color_scheme=ft.ColorScheme(
            primary=ACCENT,
            surface=BG_SURFACE,
            background=BG_DARK,
            on_primary=TEXT_PRIMARY,
            on_surface=TEXT_PRIMARY,
            on_background=TEXT_PRIMARY,
            secondary=ACCENT_SOFT,
        ),
        visual_density=ft.VisualDensity.COMPACT,
        font_family=FONT_FAMILY,
    )
