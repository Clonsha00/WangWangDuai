"""
view_home.py
------------
首頁儀表板 MVP
"""

import flet as ft
from datetime import date
import os

from theme import (
    BG_PANEL, BG_SURFACE, BG_HOVER,
    ACCENT, SUCCESS, DANGER, WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DISABLED,
    PAD_SM, PAD_MD, PAD_LG, PAD_XL,
    RADIUS_MD, RADIUS_LG,
)
from database import (
    get_actions, get_monthly_summary, get_nodes, get_habits, get_habit_log_today
)

class _HomeView(ft.Column):
    def __init__(self, on_navigate):
        super().__init__(expand=True, spacing=0, scroll=ft.ScrollMode.AUTO)
        self.on_navigate = on_navigate
        self._today = date.today().isoformat()
        self._month = date.today().strftime("%Y-%m")
        self._assemble()

    def _assemble(self):
        # 取得統計資料
        # 1. 行動 (待辦 + 習慣)
        todos = [t for t in get_actions() if t["status"] != "done"]
        todo_count = len(todos)
        
        habits = get_habits()
        logs = get_habit_log_today(self._today)
        habit_done = sum(1 for h in habits if logs.get(h["id"], False))
        habit_total = len(habits)

        # 2. 財務
        summary = get_monthly_summary(self._month)
        net = summary["net"]
        net_color = SUCCESS if net >= 0 else DANGER

        # 3. 知識庫
        nodes = get_nodes()
        node_count = len(nodes)

        # 標頭
        header = ft.Container(
            padding=ft.padding.only(left=PAD_LG, right=PAD_LG, top=PAD_LG, bottom=PAD_LG),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text("探索首頁", size=24, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Text("歡迎回來，這是您目前的概況。", size=14, color=TEXT_SECONDARY),
                ]
            )
        )

        def dashboard_card(title, value_ctrl, desc, icon, route, color):
            return ft.Container(
                expand=True,
                padding=PAD_LG,
                bgcolor=BG_PANEL,
                border_radius=RADIUS_LG,
                border=ft.border.all(1, BG_SURFACE),
                on_click=lambda _: self.on_navigate(route),
                on_hover=lambda e: self._on_hover(e),
                content=ft.Column(
                    spacing=PAD_MD,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(title, size=14, color=TEXT_SECONDARY, weight=ft.FontWeight.W_600),
                                ft.Icon(icon, color=color, size=24),
                            ]
                        ),
                        value_ctrl,
                        ft.Text(desc, size=12, color=TEXT_DISABLED),
                    ]
                )
            )

        cards_row = ft.Row(
            spacing=PAD_LG,
            controls=[
                dashboard_card(
                    "行動中樞",
                    ft.Column(
                        spacing=4,
                        controls=[
                            ft.Text(f"{todo_count} 項待辦", size=24, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Text(f"今日習慣: {habit_done}/{habit_total}", size=13, color=ACCENT),
                        ]
                    ),
                    "點擊進入 GTD 與習慣打卡",
                    ft.Icons.CHECK_CIRCLE_OUTLINE,
                    "action",
                    ACCENT
                ),
                dashboard_card(
                    "財務概況",
                    ft.Text(f"NT$ {net:,.0f}", size=24, weight=ft.FontWeight.BOLD, color=net_color),
                    f"{self._month} 淨餘結算",
                    ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                    "finance",
                    net_color
                ),
                dashboard_card(
                    "知識庫",
                    ft.Text(f"{node_count} 則筆記", size=24, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    "Zettelkasten 卡片盒",
                    ft.Icons.LIGHTBULB_OUTLINE,
                    "knowledge",
                    WARNING
                )
            ]
        )

        self.controls = [
            header,
            ft.Container(
                padding=ft.padding.symmetric(horizontal=PAD_LG),
                content=cards_row
            )
        ]

    def _on_hover(self, e: ft.HoverEvent):
        e.control.bgcolor = BG_HOVER if e.data == "true" else BG_PANEL
        e.control.update()


def HomeView(on_navigate) -> ft.Control:
    return _HomeView(on_navigate)
