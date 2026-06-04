"""
main.py
-------
應用程式進入點。
職責：
  1. 初始化 DB
  2. 建立整體 Row 佈局：Sidebar (固定) + 右側視圖 (動態)
  3. 管理路由狀態，切換視圖時只替換右側 content
"""

import flet as ft
import sys
import os

# 讓 Python 找得到同層模組
sys.path.insert(0, os.path.dirname(__file__))

from theme import build_theme, BG_DARK, BG_PANEL, BG_SURFACE, TEXT_SECONDARY, SIDEBAR_WIDTH
from database import init_db, auto_backup_db
from components.sidebar import Sidebar
from views.view_action    import ActionView
from views.view_finance   import FinanceView
from views.view_knowledge import KnowledgeView
from views.view_home      import HomeView
from views.view_calendar  import CalendarView



# ── 路由 → View 工廠函式 ──────────────────────────────
def get_view(route: str, on_navigate_cb):
    if route == "home":      return HomeView(on_navigate_cb)
    if route == "action":    return ActionView()
    if route == "calendar":  return CalendarView()
    if route == "finance" or route.startswith("finance/"): 
        # 暫時回傳原本的 FinanceView，Step 11-C 會修改它以吃 route 參數
        try:
            return FinanceView(route=route, on_navigate_cb=on_navigate_cb)
        except TypeError:
            return FinanceView() # Fallback for Step 11-B
    if route == "knowledge": return KnowledgeView()
    return HomeView(on_navigate_cb)

DEFAULT_ROUTE = "home"


def main(page: ft.Page):
    # ── 視窗設定 ──────────────────────────────────────
    page.title = "Daily Management System"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = build_theme()
    page.bgcolor = BG_DARK
    page.padding = 0
    page.spacing = 0
    page.window.width  = 1100
    page.window.height = 720
    page.window.min_width  = 800
    page.window.min_height = 500

    # ── DB 初始化 ──────────────────────────────────────
    auto_backup_db()
    init_db()

    # ── 狀態 ──────────────────────────────────────────
    current_route = DEFAULT_ROUTE

    # ── 右側視圖容器 ──────────────────────────────────
    view_container = ft.Container(
        expand=True,
        bgcolor=BG_DARK,
        content=None,
    )

    # ── Sidebar ────────────────────────────────────────
    def on_navigate(route: str):
        nonlocal current_route
        if route == current_route and view_container.content is not None:
            return
        current_route = route
        sidebar.update_active(route)
        view_container.content = get_view(route, on_navigate)
        view_container.update()

    # 初始載入視圖
    view_container.content = get_view(current_route, on_navigate)

    sidebar = Sidebar(active_route=current_route, on_navigate=on_navigate)

    sidebar_container = ft.Container(
        width=SIDEBAR_WIDTH,
        bgcolor=BG_PANEL,
        content=sidebar,
        # 右側加一條細分隔線
        border=ft.border.only(right=ft.BorderSide(1, BG_SURFACE)),
    )

    # ── 主佈局 ────────────────────────────────────────
    page.add(
        ft.Row(
            expand=True,
            spacing=0,
            controls=[
                sidebar_container,
                view_container,
            ],
        )
    )


if __name__ == "__main__":
    ft.app(target=main)
